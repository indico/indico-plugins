# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import errno
import json
import os
import re
import stat
import subprocess
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from operator import itemgetter

import boto3
import click
from botocore.exceptions import ClientError
from flask.cli import with_appcontext
from jinja2.filters import do_filesizeformat
from sqlalchemy import inspect
from sqlalchemy.orm import joinedload, lazyload, load_only
from sqlalchemy.sql.elements import Tuple
from sqlalchemy.util.compat import b64encode

from indico.cli.core import cli_group
from indico.core.config import config
from indico.core.db import db
from indico.core.storage import StoredFileMixin
from indico.core.storage.backend import FileSystemStorage, get_storage
from indico.modules.designer.models.images import DesignerImageFile
from indico.modules.events.abstracts.models.files import AbstractFile
from indico.modules.events.layout.models.images import ImageFile
from indico.modules.events.papers.models.files import PaperFile
from indico.modules.events.papers.models.templates import PaperTemplate
from indico.modules.events.registration.models.registrations import RegistrationData
from indico.modules.events.static.models.static import StaticSite, StaticSiteState
from indico.modules.files.models.files import File
from indico.util.console import cformat
from indico.util.date_time import format_human_timedelta
from indico.util.fs import secure_filename
from indico.util.iterables import committing_iterator
from indico.util.string import crc32

from indico_storage_s3.storage import S3StorageBase


SPECIAL_FILTERS = {
    StaticSite: {'state': StaticSiteState.success}
}

FILE_DT_MAP = {
    AbstractFile: lambda obj: obj.abstract.submitted_dt,
    DesignerImageFile: lambda obj: obj.template.event.created_dt if obj.template.event else None,
    ImageFile: lambda obj: obj.event.created_dt,
    PaperFile: lambda obj: obj.paper_revision.submitted_dt,
    PaperTemplate: lambda obj: obj.event.created_dt,
    RegistrationData: lambda obj: obj.registration.submitted_dt,
    StaticSite: lambda obj: obj.event.created_dt
}

QUERY_OPTIONS = {
    AbstractFile: joinedload('abstract').load_only('submitted_dt'),
    DesignerImageFile: joinedload('template').joinedload('event').load_only('created_dt'),
    ImageFile: joinedload('event').load_only('created_dt'),
    PaperFile: joinedload('paper_revision').load_only('submitted_dt'),
    PaperTemplate: joinedload('event').load_only('created_dt'),
    RegistrationData: joinedload('registration').load_only('submitted_dt'),
    StaticSite: joinedload('event').load_only('created_dt'),
}


def rmlinktree(path):
    # based on shutil.rmtree but only delete symlinks and directories
    names = os.listdir(path)
    for name in names:
        fullname = os.path.join(path, name)
        mode = os.lstat(fullname).st_mode
        if stat.S_ISDIR(mode):
            rmlinktree(fullname)
        elif stat.S_ISLNK(mode):
            os.remove(fullname)
        else:
            raise Exception(f'Tried to delete {fullname} (not a directory/symlink)')
    os.rmdir(path)


class S3Importer:
    def __init__(self, get_bucket_name, static_bucket_name, output_file, source_backend_names, rclone_remote,
                 s3_endpoint, s3_profile, s3_bucket_policy):
        self.get_bucket_name = get_bucket_name
        self.static_bucket_name = static_bucket_name
        self.source_backend_names = source_backend_names
        self.output_file = output_file
        self.s3_endpoint = s3_endpoint
        self.s3_bucket_policy = s3_bucket_policy
        self.buckets = {}
        self.s3 = boto3.session.Session(profile_name=s3_profile).resource('s3', endpoint_url=s3_endpoint)
        self.s3_client = boto3.session.Session(profile_name=s3_profile).client('s3', endpoint_url=s3_endpoint)
        self.rclone_remote = rclone_remote
        self.rclone_queue = {}
        self.used_storage_paths = set()

    def query_chunked(self, model, chunk_size):
        pks = inspect(model).primary_key
        query = base_query = self.make_query(model).order_by(*pks)
        while True:
            row = None
            for row in query.limit(chunk_size):
                yield row
            if row is None:
                # no rows in the query
                break
            query = base_query.filter(Tuple(*pks) > inspect(row).identity)

    def make_query(self, model):
        cols = ['storage_backend', 'storage_file_id', 'md5']
        if model.add_file_date_column:
            cols.append('created_dt')
        opts = QUERY_OPTIONS.get(model)
        return (model.query
                .filter(model.storage_file_id.isnot(None), model.storage_backend.in_(self.source_backend_names))
                .filter_by(**SPECIAL_FILTERS.get(model, {}))
                .options(*((opts,) if opts else ()))
                .options(lazyload('*'), load_only(*cols)))

    def run(self):
        models = {model: self.make_query(model).count() for model in StoredFileMixin.__subclasses__()}
        models = {model: total for model, total in models.items() if total}
        labels = {model: cformat('Processing %{blue!}{}%{reset} (%{cyan}{}%{reset} rows)').format(model.__name__, total)
                  for model, total in models.items()}
        max_length = max(len(x) for x in labels.values())
        labels = {model: label.ljust(max_length) for model, label in labels.items()}
        for model, total in sorted(list(models.items()), key=itemgetter(1)):
            with click.progressbar(self.query_chunked(model, 1000), length=total, label=labels[model],
                                   show_percent=True, show_pos=True) as objects:
                for obj in self.flush_rclone_iterator(objects, 1000):
                    try:
                        self.process_obj(obj)
                    except Exception as exc:
                        click.echo(cformat('\n%{red!}Error processing %{reset}%{yellow}{}%{red!}: %{reset}%{yellow!}{}')
                                   .format(obj, exc))
        click.secho('All done!', fg='green')
        click.echo('Add the following entries to your STORAGE_BACKENDS:')
        for bucket, data in sorted(self.buckets.items(), key=itemgetter(0)):
            click.echo("'{}': 's3-readonly:host={},bucket={}',".format(
                data['backend'], self.s3_endpoint.replace('https://', ''), bucket))

    def process_obj(self, obj):
        new_storage_path, new_filename = self.build_storage_path(obj)
        if new_storage_path in self.used_storage_paths:
            raise Exception(f'Non-unique storage path: {new_storage_path}')
        self.used_storage_paths.add(new_storage_path)
        bucket_name, backend = self.get_bucket_name(self.get_object_dt(obj))
        bucket_info = self.get_bucket_info(bucket_name, backend, create=(not self.rclone_remote))
        assert backend == bucket_info['backend']
        if new_storage_path not in bucket_info['initial_keys']:
            if self.rclone_remote:
                self.queue_for_rclone(obj, bucket_name, new_storage_path)
            else:
                with obj.open() as f:
                    content_md5 = b64encode(bytes.fromhex(obj.md5)).decode().strip()
                    self.s3_client.put_object(Body=f, Bucket=bucket_name, Key=new_storage_path,
                                              ContentType=obj.content_type, ContentMD5=content_md5)
        self.emit_update(obj, backend, new_storage_path, new_filename)

    def build_storage_path(self, obj, _new_path_re=re.compile(r'^(event/\d+/registrations/\d+/\d+/\d+-)(\d+)(-.*)$')):
        if isinstance(obj, File):
            # ``File``` was added in 2.3 and thus always has the correct paths
            # we cannot re-generate the storage path for it since it uses
            # a __context attribute which is only present during the initial
            # `save()` call and not stored anywhere.
            return obj.storage_file_id, obj.filename
        old_filename = obj.filename
        new_filename = secure_filename(obj.filename, None)
        assert new_filename
        obj.filename = new_filename
        new_storage_path = obj._build_storage_path()[1]
        obj.filename = old_filename
        assert new_storage_path
        if not isinstance(obj, RegistrationData):
            return new_storage_path, new_filename
        match = _new_path_re.match(obj.storage_file_id)
        if match:
            # already in the current format
            assert obj.storage_file_id == new_storage_path.replace('-0-', f'-{match.group(2)}-')
            return obj.storage_file_id, new_filename
        else:
            match = _new_path_re.match(new_storage_path)
            return f'{match.group(1)}{crc32(obj.storage_file_id)}{match.group(3)}', new_filename

    def queue_for_rclone(self, obj, bucket, key):
        # XXX: we assume the file is local so the context manager doesn't create a
        # temporary file which becomes invalid afterwards
        with obj.get_local_path() as file_path:
            pass
        while not os.path.exists(file_path):
            input(cformat('\n%{red}File not found on disk: %{yellow}{}').format(file_path))
        try:
            queue_entry = self.rclone_queue[bucket]
        except KeyError:
            tmpdir = tempfile.mkdtemp(prefix='indico-s3-import-')
            self.rclone_queue[bucket] = queue_entry = {
                'path': tmpdir,
                'files': 0,
                'bytes': 0,
            }
        fskey = os.path.join(queue_entry['path'], key)
        fsdir = os.path.dirname(fskey)
        try:
            os.makedirs(fsdir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        os.symlink(file_path, fskey)
        queue_entry['files'] += 1
        queue_entry['bytes'] += obj.size

    def flush_rclone_iterator(self, iterable, n=100):
        for i, data in enumerate(iterable, 1):
            yield data
            if i % n == 0:
                self.flush_rclone()
                db.session.rollback()  # reduce memory usage
        self.flush_rclone()

    def flush_rclone(self):
        if not self.rclone_remote or not self.rclone_queue:
            return
        click.echo()
        for name, data in self.buckets.items():
            if not data['exists']:
                self.create_bucket(name)
                data['exists'] = True
        for bucket, data in self.rclone_queue.items():
            click.echo(cformat('Copying %{cyan}{}%{reset} files (%{cyan}{}%{reset}) to %{cyan}{}%{reset} via rclone')
                       .format(data['files'], do_filesizeformat(data['bytes']), bucket))
            start = datetime.now()
            try:
                subprocess.check_call([
                    'rclone', 'copy', '--copy-links',
                    data['path'], f'{self.rclone_remote}:{bucket}'
                ])
            except subprocess.CalledProcessError:
                click.secho('\nError while running rclone', fg='red')
                raise
            duration = (datetime.now() - start)
            click.echo('...finished after {}'.format(format_human_timedelta(duration, 'minutes', narrow=True)))
            rmlinktree(data['path'])
        self.rclone_queue.clear()

    def bucket_exists(self, name):
        try:
            self.s3_client.head_bucket(Bucket=name)
            return True
        except ClientError as exc:
            if int(exc.response['Error']['Code']) == 404:
                return False
            raise

    def create_bucket(self, name):
        click.echo(cformat('Creating bucket %{green}{}%{reset}').format(name))
        self.s3_client.create_bucket(Bucket=name)
        if self.s3_bucket_policy:
            self.s3_client.put_bucket_policy(Bucket=name, Policy=self.s3_bucket_policy)

    def get_bucket_info(self, bucket_name, backend, create=False):
        try:
            return self.buckets[bucket_name]
        except KeyError:
            click.echo(cformat('\nChecking bucket %{yellow}{}%{reset}').format(bucket_name))
            exists = True
            if not self.bucket_exists(bucket_name):
                if create:
                    click.echo()
                    self.create_bucket(bucket_name)
                else:
                    exists = False

            data = {'backend': backend, 'exists': exists}
            if exists:
                bucket = self.s3.Bucket(bucket_name)
                data['initial_keys'] = {f.key for f in bucket.objects.all()}
            else:
                data['initial_keys'] = set()
            self.buckets[bucket_name] = data
            return data

    def get_object_dt(self, obj):
        cls = type(obj)
        if cls.add_file_date_column:
            return obj.created_dt
        fn = FILE_DT_MAP.get(cls) or (lambda _: datetime.now())
        return fn(obj)

    def emit_update(self, obj, backend, file_id, filename):
        data = {'m': type(obj).__name__, 'pk': inspect(obj).identity}
        if obj.storage_backend != backend:
            data.update({
                'ob': obj.storage_backend,
                'nb': backend,
            })
        if obj.storage_file_id != file_id:
            data.update({
                'of': obj.storage_file_id,
                'nf': file_id,
            })
        if obj.filename != filename:
            data.update({
                'on': obj.filename,
                'nn': filename,
            })
        json.dump(data, self.output_file)
        self.output_file.write('\n')


def apply_changes(data_file, revert=False):
    mapping = {
        'pk': 'pk',
        'ob': 'old_storage_backend',
        'nb': 'new_storage_backend',
        'of': 'old_storage_file_id',
        'nf': 'new_storage_file_id',
        'on': 'old_filename',
        'nn': 'new_filename',
    }
    click.echo('Parsing data...')
    data = defaultdict(list)
    for line in data_file:
        line_data = json.loads(line)
        converted = {mapping[k]: v for k, v in line_data.items() if k in mapping}
        data[line_data['m']].append(converted)

    models = {model: len(data[model.__name__])
              for model in StoredFileMixin.__subclasses__()
              if model.__name__ in data and len(data[model.__name__])}
    labels = {model: cformat('Processing %{blue!}{}%{reset} (%{cyan}{}%{reset} rows)').format(model.__name__, total)
              for model, total in models.items()}
    max_length = max(len(x) for x in labels.values())
    labels = {model: label.ljust(max_length) for model, label in labels.items()}
    for model, total in sorted(list(models.items()), key=itemgetter(1)):
        pks = inspect(model).primary_key
        with click.progressbar(data[model.__name__], length=total, label=labels[model],
                               show_percent=True, show_pos=True) as entries:
            for entry in committing_iterator(entries, 1000):
                updates = {}
                key = 'old' if revert else 'new'
                if key + '_storage_backend' in entry:
                    updates[model.storage_backend] = entry[key + '_storage_backend']
                if key + '_storage_file_id' in entry:
                    updates[model.storage_file_id] = entry[key + '_storage_file_id']
                if key + '_filename' in entry:
                    updates[model.filename] = entry[key + '_filename']
                model.query.filter(Tuple(*pks) == entry['pk']).update(updates, synchronize_session=False)


@contextmanager
def monkeypatch_registration_file_time():
    # RegistrationData objects have the current timestamp in their
    # storage_file_id to ensure uniqueness in case lf re-upload, but
    # here we want reliable filenames
    from indico.modules.events.registration.models import registrations

    class FakeTime:
        def time(self):
            return 0

    orig_time = registrations.time
    registrations.time = FakeTime()
    yield
    registrations.time = orig_time


@cli_group()
@with_appcontext
def cli():
    """Migrate data to S3.

    Use the `copy` subcommand to copy data to S3. This can be done
    safely while Indico is running. At the end it will show you what
    you need to add to your `indico.conf`.

    Once you updated your config with the new storage backends, you
    can use the `apply` subcommand to update your database so files
    will actually be loaded using the new S3 storage backends.

    In case you ever need to switch back to your previous storage,
    you can use `revert` to undo the database changes.
    """
    if config.DB_LOG:
        click.secho('Warning: The database logger is currently enabled (DB_LOG = True).\n'
                    'This will slow down the migration. Unless you database is very small, please disable it.',
                    fg='yellow')
        click.confirm('Continue anyway?', abort=True)


@cli.command()
@click.option('-s', '--source-backend', 'source_backend_names', metavar='NAME', multiple=True,
              help='Storage backend names from which to copy files. If omitted, all non-S3 backends are used.')
@click.option('-B', '--bucket-name', 'bucket_names', metavar='NAME', required=True, multiple=True,
              help='Bucket(s) to copy files to')
@click.option('-S', '--static-bucket-name', metavar='NAME', required=True,
              help='Bucket to copy static site packages to')
@click.option('-e', '--s3-endpoint', metavar='URL', help='Custom S3 endpoint, e.g. https://s3.example.com')
@click.option('-p', '--s3-profile', metavar='NAME', help='S3 profile to use when loading credentials')
@click.option('-P', '--s3-bucket-policy', 's3_bucket_policy_file', metavar='PATH', type=click.File(),
              help='Bucket policy file to use when creating buckets')
@click.option('-r', '--rclone', metavar='NAME',
              help='If set, use rclone to copy files which is usually faster. The value of this option is the name of '
                   'the rclone remote used to copy files to S3.')
@click.argument('output', metavar='PATH', type=click.File('wb'))
def copy(source_backend_names, bucket_names, static_bucket_name, s3_endpoint, s3_profile, s3_bucket_policy_file,
         rclone, output):
    """Copy files to S3.

    This command copies files to S3 and records the necessary database changes
    in a JSONL file.

    Multiple bucket names can be specified; in that case the bucket name can change
    based on the year a file was created in. The last bucket name will be the default,
    while any other bucket name must include a conditional indicating when to use it:

    \b
        -B '<2001:indico-pre-2001'
        -B '<2009:indico-<year>'
        -B 'indico-<year>-<month>'

    The static bucket name cannot contain any placeholders.

    The indico storage backend will get the same name as the bucket by default,
    but this can be overridden, e.g. `-B 'indico-<year>/s3-<year>'` would name
    the bucket 'indico-2018' but use a backend named 's3-2018'.  It is your
    responsibility to ensure that placeholders match between the two names.

    S3 credentials should be specified in the usual places, i.e.
    `~/.aws/credentials` for regular S3 access and `~/.config/rclone/rclone.conf`
    when using rclone.
    """
    bucket_names = [tuple(x.split('/', 1)) if '/' in x else (x, x.split(':', 1)[-1]) for x in bucket_names]
    if ':' in bucket_names[-1][0]:
        raise click.UsageError('Last bucket name cannot contain criteria')
    if not all(':' in x[0] for x in bucket_names[:-1]):
        raise click.UsageError('All but the last bucket name need to contain criteria')
    matches = [(re.match(r'^(<|>|==|<=|>=)\s*(\d{4}):(.+)$', name), backend) for name, backend in bucket_names[:-1]]
    if not all(x[0] for x in matches):
        raise click.UsageError(f"Could not parse '{bucket_names[matches.index(None)]}'")
    criteria = [(match.groups(), backend) for match, backend in matches]
    # Build and compile a function to get the bucket/backend name to avoid
    # processing the criteria for every single file (can be millions for large
    # instances)
    code = ['def get_bucket_name(dt):']
    if criteria:
        for i, ((op, value, bucket), backend) in enumerate(criteria):
            code.append('    {}if dt.year {} {}:'.format('el' if i else '', op, value))
            code.append(f'        bucket, backend = {(bucket, backend)!r}')
        code.append('    else:')
        code.append(f'        bucket, backend = {bucket_names[-1]!r}')
    else:
        code.append(f'    bucket, backend = {bucket_names[-1]!r}')
    code.append('    bucket = bucket.replace("<year>", dt.strftime("%Y"))')
    code.append('    bucket = bucket.replace("<month>", dt.strftime("%m"))')
    code.append('    bucket = bucket.replace("<week>", dt.strftime("%W"))')
    code.append('    backend = backend.replace("<year>", dt.strftime("%Y"))')
    code.append('    backend = backend.replace("<month>", dt.strftime("%m"))')
    code.append('    backend = backend.replace("<week>", dt.strftime("%W"))')
    code.append('    return bucket, backend')
    d = {}
    exec('\n'.join(code), d)
    if not source_backend_names:
        source_backend_names = [x for x in config.STORAGE_BACKENDS if not isinstance(get_storage(x), S3StorageBase)]
    if rclone:
        invalid = [x for x in source_backend_names if not isinstance(get_storage(x), FileSystemStorage)]
        if invalid:
            click.secho('Found unsupported storage backends: {}'.format(', '.join(sorted(invalid))), fg='yellow')
            click.secho('The backends might not work together with `--rclone`', fg='yellow')
            click.confirm('Continue anyway?', abort=True)
    s3_bucket_policy = s3_bucket_policy_file.read() if s3_bucket_policy_file else None
    imp = S3Importer(d['get_bucket_name'], static_bucket_name,
                     output, source_backend_names, rclone,
                     s3_endpoint, s3_profile, s3_bucket_policy)
    with monkeypatch_registration_file_time():
        imp.run()


@cli.command()
@click.argument('data', metavar='PATH', type=click.File('rb'))
def apply(data):
    """Apply DB updates.

    This command updates the DB with the changes recorded while
    running the `copy` command.
    """
    apply_changes(data)


@cli.command()
@click.argument('data', metavar='PATH', type=click.File('rb'))
def revert(data):
    """Revert DB updates.

    This command reverts the changes made to the database by the
    `apply` command.
    """
    apply_changes(data, revert=True)
