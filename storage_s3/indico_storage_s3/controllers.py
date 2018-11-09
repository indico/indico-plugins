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

from flask import current_app, jsonify, request
from werkzeug.exceptions import NotFound, Unauthorized

from indico.core.config import config
from indico.core.db import db
from indico.core.storage import StoredFileMixin
from indico.core.storage.backend import ReadOnlyStorageMixin, get_storage
from indico.web.rh import RH

from indico_storage_s3.storage import DynamicS3Storage, S3Storage, S3StorageBase


class RHBuckets(RH):
    """Provide information on used S3 buckets"""

    def _check_access(self):
        from indico_storage_s3.plugin import S3StoragePlugin
        auth = request.authorization
        if not S3StoragePlugin.settings.get('bucket_info_enabled'):
            raise NotFound
        username = S3StoragePlugin.settings.get('username')
        password = S3StoragePlugin.settings.get('password')
        if not auth or not auth.password or auth.username != username or auth.password != password:
            response = current_app.response_class('Authorization required', 401,
                                                  {'WWW-Authenticate': 'Basic realm="Indico - S3 Buckets"'})
            raise Unauthorized(response=response)

    def _get_static_info(self, storage):
        return {
            'bucket': storage.bucket_name,
            'dynamic': False,
        }

    def _get_dynamic_info(self, backend_name, storage):
        buckets = set()
        for model in StoredFileMixin.__subclasses__():
            query = (db.session.query(db.func.split_part(model.storage_file_id, '//', 1).distinct())
                     .filter(model.storage_file_id.isnot(None), model.storage_backend == backend_name))
            buckets.update(bucket for bucket, in query)

        return {
            'buckets': sorted(buckets),
            'dynamic': True,
            'template': storage.bucket_name_template,
        }

    def _process(self):
        data = {}
        for key in config.STORAGE_BACKENDS:
            storage = get_storage(key)
            if not isinstance(storage, S3StorageBase):
                continue
            readonly = isinstance(storage, ReadOnlyStorageMixin)
            data[key] = {'readonly': readonly, 'meta': storage.meta}
            if isinstance(storage, S3Storage):
                data[key].update(self._get_static_info(storage))
            elif isinstance(storage, DynamicS3Storage):
                data[key].update(self._get_dynamic_info(key, storage))
        return jsonify(data)
