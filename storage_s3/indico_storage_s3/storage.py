# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import hashlib
import hmac
import sys
import threading
from contextlib import contextmanager
from datetime import date
from enum import Enum
from io import BytesIO
from tempfile import NamedTemporaryFile

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from werkzeug.datastructures import Headers
from werkzeug.utils import cached_property, redirect

from indico.core.config import config
from indico.core.storage import Storage, StorageError
from indico.core.storage.backend import ReadOnlyStorageMixin, StorageReadOnlyError
from indico.util.fs import get_file_checksum
from indico.util.string import return_ascii
from indico.web.flask.util import send_file


s3_session_cache = threading.local()


class ProxyDownloadsMode(Enum):
    disabled = 0
    local = 1
    nginx = 2


class S3StorageBase(Storage):
    simple_data = False

    def __init__(self, data):
        self.parsed_data = data = self._parse_data(data)
        self.endpoint_url = data.get('host')
        if self.endpoint_url and '://' not in self.endpoint_url:
            self.endpoint_url = 'https://' + self.endpoint_url
        self.session_kwargs = {}
        self.client_kwargs = {}
        if 'profile' in data:
            self.session_kwargs['profile_name'] = data['profile']
        if 'access_key' in data:
            self.session_kwargs['aws_access_key_id'] = data['access_key']
        if 'secret_key' in data:
            self.session_kwargs['aws_secret_access_key'] = data['secret_key']
        if 'addressing_style' in data:
            self.client_kwargs['config'] = Config(s3={'addressing_style': data['addressing_style']})
        self.bucket_policy_file = data.get('bucket_policy_file')
        self.bucket_versioning = data.get('bucket_versioning') in ('1', 'true', 'yes', 'on')
        if data.get('proxy') in ('1', 'true', 'yes', 'on'):
            self.proxy_downloads = ProxyDownloadsMode.local
        elif data.get('proxy') in ('xaccelredirect', 'nginx'):
            self.proxy_downloads = ProxyDownloadsMode.nginx
        else:
            self.proxy_downloads = ProxyDownloadsMode.disabled
        self.meta = data.get('meta')

    @cached_property
    def session(self):
        key = '__'.join('{}_{}'.format(k, v) for k, v in sorted(self.session_kwargs.viewitems()))
        try:
            return getattr(s3_session_cache, key)
        except AttributeError:
            session = boto3.session.Session(**self.session_kwargs)
            setattr(s3_session_cache, key, session)
            return session

    @cached_property
    def client(self):
        return self.session.client('s3', endpoint_url=self.endpoint_url, **self.client_kwargs)

    def _get_current_bucket_name(self):
        raise NotImplementedError

    def _parse_file_id(self, file_id):
        raise NotImplementedError

    def open(self, file_id):
        bucket, id_ = self._parse_file_id(file_id)
        try:
            s3_object = self.client.get_object(Bucket=bucket, Key=id_)['Body']
            return BytesIO(s3_object.read())
        except Exception as e:
            raise StorageError('Could not open "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    @contextmanager
    def get_local_path(self, file_id):
        with NamedTemporaryFile(suffix='indico.s3', dir=config.TEMP_DIR) as tmpfile:
            self._copy_file(self.open(file_id), tmpfile)
            tmpfile.flush()
            yield tmpfile.name

    def _save(self, bucket, name, content_type, fileobj):
        fileobj = self._ensure_fileobj(fileobj)
        checksum = get_file_checksum(fileobj)
        fileobj.seek(0)
        content_md5 = checksum.decode('hex').encode('base64').strip()
        self.client.put_object(Body=fileobj, Bucket=bucket, Key=name,
                               ContentType=content_type, ContentMD5=content_md5)
        return checksum

    def delete(self, file_id):
        bucket, id_ = self._parse_file_id(file_id)
        try:
            self.client.delete_object(Bucket=bucket, Key=id_)
        except Exception as e:
            raise StorageError('Could not delete "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def getsize(self, file_id):
        bucket, id_ = self._parse_file_id(file_id)
        try:
            return self.client.head_object(Bucket=bucket, Key=id_)['ContentLength']
        except Exception as e:
            raise StorageError('Could not get size of "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def send_file(self, file_id, content_type, filename, inline=True):
        if self.proxy_downloads == ProxyDownloadsMode.local:
            return send_file(filename, self.open(file_id), content_type, inline=inline)

        try:
            bucket, id_ = self._parse_file_id(file_id)
            content_disp = 'inline' if inline else 'attachment'
            h = Headers()
            h.add('Content-Disposition', content_disp, filename=filename)
            url = self.client.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket,
                                                             'Key': id_,
                                                             'ResponseContentDisposition': h.get('Content-Disposition'),
                                                             'ResponseContentType': content_type},
                                                     ExpiresIn=120)
            response = redirect(url)
            if self.proxy_downloads == ProxyDownloadsMode.nginx:
                # nginx can proxy the request to S3 to avoid exposing the redirect and
                # bucket URL to the end user (since it is quite ugly and temporary)
                response.headers['X-Accel-Redirect'] = '/.xsf/s3/' + url.replace('://', '/', 1)
            return response
        except Exception as e:
            raise StorageError('Could not send file "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def _create_bucket(self, name):
        from indico_storage_s3.plugin import S3StoragePlugin

        if self._bucket_exists(name):
            S3StoragePlugin.logger.info('Bucket %s already exists', name)
            return
        self.client.create_bucket(Bucket=name)
        S3StoragePlugin.logger.info('New bucket created: %s', name)
        if self.bucket_versioning:
            self.client.put_bucket_versioning(Bucket=name, VersioningConfiguration={'Status': 'Enabled'})
        if self.bucket_policy_file:
            with open(self.bucket_policy_file) as f:
                policy = f.read()
            self.client.put_bucket_policy(Bucket=name, Policy=policy)

    def _bucket_exists(self, name):
        try:
            self.client.head_bucket(Bucket=name)
            return True
        except ClientError as exc:
            if int(exc.response['Error']['Code']) == 404:
                return False
            raise


class S3Storage(S3StorageBase):
    name = 's3'

    def __init__(self, data):
        super(S3Storage, self).__init__(data)
        self.bucket_name = self.parsed_data['bucket']
        if len(self.bucket_name) > 63:
            raise StorageError('Bucket name cannot be longer than 63 chars')

    @return_ascii
    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, self.bucket_name)

    def _get_current_bucket_name(self):
        return self.bucket_name

    def _parse_file_id(self, file_id):
        return self.bucket_name, file_id

    def save(self, name, content_type, filename, fileobj):
        try:
            bucket = self._get_current_bucket_name()
            checksum = self._save(bucket, name, content_type, fileobj)
            return name, checksum
        except Exception as e:
            raise StorageError('Could not save "{}": {}'.format(name, e)), None, sys.exc_info()[2]


class DynamicS3Storage(S3StorageBase):
    name = 's3-dynamic'

    def __init__(self, data):
        super(DynamicS3Storage, self).__init__(data)
        self.bucket_name_template = self.parsed_data['bucket_template']
        self.bucket_secret = (self.parsed_data.get('bucket_secret', '') or
                              self.session._session.get_scoped_config().get('indico_bucket_secret', ''))
        if not any(x in self.bucket_name_template for x in ('<year>', '<month>', '<week>')):
            raise StorageError('At least one date placeholder is required when using dynamic bucket names')
        if not self.bucket_secret:
            raise StorageError('A bucket secret is required when using dynamic bucket names')
        if len(self._replace_bucket_placeholders(self.bucket_name_template, date.today())) > 46:
            raise StorageError('Bucket name cannot be longer than 46 chars (to keep at least 16 hash chars)')

    @return_ascii
    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, self.bucket_name_template)

    def _parse_file_id(self, file_id):
        return file_id.split('//', 1)

    def _get_current_bucket_name(self):
        return self._get_bucket_name(date.today())

    def _get_bucket_name(self, date):
        name = self._replace_bucket_placeholders(self.bucket_name_template, date)
        token = hmac.new(self.bucket_secret.encode('utf-8'), name, hashlib.md5).hexdigest()
        return '{}-{}'.format(name, token)[:63]

    def _replace_bucket_placeholders(self, name, date):
        name = name.replace('<year>', date.strftime('%Y'))
        name = name.replace('<month>', date.strftime('%m'))
        name = name.replace('<week>', date.strftime('%W'))
        return name

    def save(self, name, content_type, filename, fileobj):
        try:
            bucket = self._get_current_bucket_name()
            checksum = self._save(bucket, name, content_type, fileobj)
            file_id = '{}//{}'.format(bucket, name)
            return file_id, checksum
        except Exception as e:
            raise StorageError('Could not save "{}": {}'.format(name, e)), None, sys.exc_info()[2]


class ReadOnlyS3Storage(ReadOnlyStorageMixin, S3Storage):
    name = 's3-readonly'

    def _create_bucket(self, name):
        raise StorageReadOnlyError('Cannot write to read-only storage')


class ReadOnlyDynamicS3Storage(ReadOnlyStorageMixin, DynamicS3Storage):
    name = 's3-dynamic-readonly'

    def _create_bucket(self, name):
        raise StorageReadOnlyError('Cannot write to read-only storage')
