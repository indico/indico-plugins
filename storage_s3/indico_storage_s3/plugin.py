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

import click

from indico.cli.core import cli_command
from indico.core import signals
from indico.core.config import config
from indico.core.plugins import IndicoPlugin
from indico.core.storage.backend import ReadOnlyStorageMixin, get_storage

from indico_storage_s3.storage import (DynamicS3Storage, ReadOnlyDynamicS3Storage, ReadOnlyS3Storage, S3Storage,
                                       S3StorageBase)


class S3StoragePlugin(IndicoPlugin):
    """S3 Storage

    Provides S3 storage backends.
    """

    def init(self):
        super(S3StoragePlugin, self).init()
        self.connect(signals.get_storage_backends, self._get_storage_backends)
        self.connect(signals.plugin.cli, self._extend_indico_cli)

    def _get_storage_backends(self, sender, **kwargs):
        yield S3Storage
        yield DynamicS3Storage
        yield ReadOnlyS3Storage
        yield ReadOnlyDynamicS3Storage

    def _extend_indico_cli(self, sender, **kwargs):
        @cli_command()
        @click.option('--storage', default=None, metavar='NAME', help='Storage backend to create bucket for')
        def create_s3_bucket(storage):
            """Create s3 storage bucket."""
            storages = [storage] if storage else config.STORAGE_BACKENDS
            for key in storages:
                try:
                    storage_instance = get_storage(key)
                except RuntimeError:
                    if storage:
                        click.echo('Storage {} does not exist'.format(key))
                        sys.exit(1)
                    continue

                if isinstance(storage_instance, ReadOnlyStorageMixin):
                    if storage:
                        click.echo('Storage {} is read-only'.format(key))
                        sys.exit(1)
                    continue

                if isinstance(storage_instance, S3StorageBase):
                    bucket_name = storage_instance._get_current_bucket_name()
                    if storage_instance._bucket_exists(bucket_name):
                        click.echo('Storage {}: bucket {} already exists'.format(key, bucket_name))
                        continue
                    storage_instance._create_bucket(bucket_name)
                    click.echo('Storage {}: bucket {} created'.format(key, bucket_name))
                elif storage:
                    click.echo('Storage {} is not a s3 storage'.format(key))
                    sys.exit(1)

        return create_s3_bucket
