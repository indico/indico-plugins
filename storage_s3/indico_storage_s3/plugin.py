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
from tempfile import NamedTemporaryFile

import boto3

from indico.core import signals
from indico.core.config import config
from indico.core.plugins import IndicoPlugin
from indico.core.storage import Storage, StorageError
from indico.web.flask.util import send_file


class S3StoragePlugin(IndicoPlugin):
    """S3 Storage

    Provides S3 storage backends.
    """

    def init(self):
        super(S3StoragePlugin, self).init()
        self.connect(signals.get_storage_backends, self._get_storage_backends)

    def _get_storage_backends(self, sender, **kwargs):
        return S3Storage


class S3Storage(Storage):
    name = 's3'
    simple_data = False

    def __init__(self, data):
        data = self._parse_data(data)
        self.host = data['host']
        self.bucket = data['bucket']
        self.secret_key = data['secret_key']
        self.access_key = data['access_key']
        self.client = boto3.client(
            's3',
            endpoint_url=self.host,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def open(self, file_id):
        try:
            return self.client.get_object(Bucket=self.bucket, Key=file_id)['Body']
        except Exception as e:
            raise StorageError('Could not open "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    @contextmanager
    def get_local_path(self, file_id):
        with NamedTemporaryFile(suffix='indico.tmp', dir=config.TEMP_DIR) as tmpfile:
            self._copy_file(self.open(file_id), tmpfile)
            tmpfile.flush()
            yield tmpfile.name

    def save(self, name, content_type, filename, fileobj):
        try:
            self.client.upload_fileobj(fileobj, self.bucket, name)
            return name, ''
        except Exception as e:
            raise StorageError('Could not save "{}": {}'.format(name, e)), None, sys.exc_info()[2]

    def delete(self, file_id):
        try:
            self.client.delete_object(self.bucket, file_id)
        except Exception as e:
            raise StorageError('Could not delete "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def getsize(self, file_id):
        try:
            return self.client.head_object(Bucket=self.bucket, Key=file_id)['ContentLength']
        except Exception as e:
            raise StorageError('Could not get size of "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]

    def send_file(self, file_id, content_type, filename, inline=True):
        try:
            fileobj = self.client.get_object(Bucket=self.bucket, Key=file_id)['Body']
            return send_file(filename, fileobj, content_type, inline=inline)
        except Exception as e:
            raise StorageError('Could not send file "{}": {}'.format(file_id, e)), None, sys.exc_info()[2]
