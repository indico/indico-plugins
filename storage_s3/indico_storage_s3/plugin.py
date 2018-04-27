# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import sys
from contextlib import contextmanager
from datetime import date
from io import BytesIO
from tempfile import NamedTemporaryFile

import boto3
import botocore
import click
from werkzeug.datastructures import Headers
from werkzeug.utils import redirect

from indico.cli.core import cli_command
from indico.core import signals
from indico.core.config import config
from indico.core.plugins import IndicoPlugin
from indico.core.storage import Storage, StorageError
from indico.core.storage.backend import get_storage
from indico.util.fs import get_file_checksum


class S3StoragePlugin(IndicoPlugin):
    """S3 Storage

    Provides S3 storage backends.
    """

    def init(self):
        super(S3StoragePlugin, self).init()
        self.connect(signals.get_storage_backends, self._get_storage_backends)
        self.connect(signals.plugin.cli, self._extend_indico_cli)

    def _get_storage_backends(self, sender, **kwargs):
        return S3Storage

    def _extend_indico_cli(self, sender, **kwargs):
        @cli_command()
        @click.option('--storage', default=None, help='Storage to create bucket for')
        def create_s3_bucket(storage):
            """Create s3 bucket"""
            storages = [storage] if storage else config.STORAGE_BACKENDS
            for key in storages:
                try:
                    storage_instance = get_storage(key)
                except RuntimeError:
                    if storage:
                        click.echo('Storage {} does not exist'.format(key))
                        sys.exit(1)
                if isinstance(storage_instance, S3Storage):
                    bucket_name = storage_instance._get_current_bucket()
                    if storage_instance._bucket_exists(bucket_name):
                        click.echo('Storage {}: bucket {} already exists'.format(key, bucket_name))
                        continue
                    storage_instance._create_bucket(bucket_name)
                    click.echo('Storage {}: bucket {} created'.format(key, bucket_name))
                elif storage:
                    click.echo('Storage {} is not a s3 storage'.format(key))
                    sys.exit(1)
        return create_s3_bucket


class S3Storage(Storage):
    name = 's3'
    simple_data = False

    def __init__(self, data):
        data = self._parse_data(data)
        self.host = data['host']
        self.bucket = data['bucket']
        self.secret_key = data['secret_key']
        self.access_key = data['access_key']
        self.acl_template_bucket = data.get('acl_template_bucket')
        self.client = boto3.client(
            's3',
            endpoint_url=self.host,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def open(self, file_id):
        try:
            s3_object = self.client.get_object(Bucket=self._get_current_bucket(), Key=file_id)['Body']
            return BytesIO(s3_object.read())
        except Exception as e:
            raise StorageError('Could not open "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    @contextmanager
    def get_local_path(self, file_id):
        with NamedTemporaryFile(suffix='indico.s3', dir=config.TEMP_DIR) as tmpfile:
            self._copy_file(self.open(file_id), tmpfile)
            tmpfile.flush()
            yield tmpfile.name

    def save(self, name, content_type, filename, fileobj):
        try:
            fileobj = self._ensure_fileobj(fileobj)
            bucket = self._get_current_bucket()
            checksum = get_file_checksum(fileobj)
            fileobj.seek(0)
            contentmd5 = checksum.decode('hex').encode('base64').strip()
            self.client.put_object(Body=fileobj, Bucket=bucket, ContentMD5=contentmd5, Key=name)
            return name, checksum
        except Exception as e:
            raise StorageError('Could not save "{}": {}'.format(name, e)), None, sys.exc_info()[2]

    def delete(self, file_id):
        try:
            self.client.delete_object(self._get_current_bucket(), file_id)
        except Exception as e:
            raise StorageError('Could not delete "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def getsize(self, file_id):
        try:
            return self.client.head_object(Bucket=self._get_current_bucket(), Key=file_id)['ContentLength']
        except Exception as e:
            raise StorageError('Could not get size of "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def send_file(self, file_id, content_type, filename, inline=True):
        try:
            content_disp = 'inline' if inline else 'attachment'
            h = Headers()
            h.add('Content-Disposition', content_disp, filename=filename)
            url = self.client.generate_presigned_url('get_object',
                                                     Params={'Bucket': self._get_current_bucket(),
                                                             'Key': file_id,
                                                             'ResponseContentDisposition': h.get('Content-Disposition'),
                                                             'ResponseContentType': content_type},
                                                     ExpiresIn=120)
            return redirect(url)
        except Exception as e:
            raise StorageError('Could not send file "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def _get_current_bucket(self):
        return self._replace_bucket_placeholders(self.bucket, date.today())

    def _get_bucket_name(self, current=False):
        return self._get_current_bucket() if current else self.bucket

    def _replace_bucket_placeholders(self, name, date):
        name = name.replace('<year>', date.strftime('%Y'))
        name = name.replace('<month>', date.strftime('%m'))
        name = name.replace('<week>', date.strftime('%W'))
        return name

    def _create_bucket(self, name):
        if self._bucket_exists(name):
            S3StoragePlugin.logger.info('Bucket %s already exists', name)
            return
        self.client.create_bucket(Bucket=name)
        S3StoragePlugin.logger.info('New bucket created: %s', name)
        if self.acl_template_bucket:
            response = self.client.get_bucket_acl(Bucket=self.acl_template_bucket)
            acl_keys = {'Owner', 'Grants'}
            acl = {key: response[key] for key in response if key in acl_keys}
            self.client.put_bucket_acl(AccessControlPolicy=acl, Bucket=name)

    def _bucket_exists(self, name):
        try:
            self.client.head_bucket(Bucket=name)
            return True
        except botocore.exceptions.ClientError:
            return False
