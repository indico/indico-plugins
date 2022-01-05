# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import sys

import click
from markupsafe import Markup
from wtforms.fields import BooleanField, StringField
from wtforms.validators import DataRequired

from indico.cli.core import cli_group
from indico.core import signals
from indico.core.config import config
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.core.storage.backend import ReadOnlyStorageMixin, get_storage
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField
from indico.web.forms.validators import HiddenUnless
from indico.web.forms.widgets import SwitchWidget

from indico_storage_s3 import _
from indico_storage_s3.blueprint import blueprint
from indico_storage_s3.migrate import cli as migrate_cli
from indico_storage_s3.storage import (DynamicS3Storage, ReadOnlyDynamicS3Storage, ReadOnlyS3Storage, S3Storage,
                                       S3StorageBase)


class SettingsForm(IndicoForm):
    bucket_info_enabled = BooleanField(_("Bucket info API"), widget=SwitchWidget())
    username = StringField(_("Username"), [HiddenUnless('bucket_info_enabled', preserve_data=True), DataRequired()],
                           description=_("The username to access the S3 bucket info endpoint"))
    password = IndicoPasswordField(_('Password'),
                                   [HiddenUnless('bucket_info_enabled', preserve_data=True), DataRequired()],
                                   toggle=True,
                                   description=_("The password to access the S3 bucket info endpoint"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        url = Markup('<strong><code>{}</code></strong>').format(url_for_plugin('storage_s3.buckets'))
        self.bucket_info_enabled.description = _("Enables an API on {url} that returns information on all S3 buckets "
                                                 "currently in use, including dynamically-named ones.").format(url=url)


class S3StoragePlugin(IndicoPlugin):
    """S3 Storage

    Provides S3 storage backends.
    """

    configurable = True
    settings_form = SettingsForm
    default_settings = {
        'bucket_info_enabled': False,
        'username': '',
        'password': ''
    }

    def init(self):
        super().init()
        self.connect(signals.core.get_storage_backends, self._get_storage_backends)
        self.connect(signals.plugin.cli, self._extend_indico_cli)

    def _get_storage_backends(self, sender, **kwargs):
        yield S3Storage
        yield DynamicS3Storage
        yield ReadOnlyS3Storage
        yield ReadOnlyDynamicS3Storage

    def get_blueprints(self):
        return blueprint

    def _extend_indico_cli(self, sender, **kwargs):
        @cli_group()
        def s3():
            """Manage S3 storage."""

        @s3.command()
        @click.option('--storage', default=None, metavar='NAME', help='Storage backend to create bucket for')
        def create_bucket(storage):
            """Create s3 storage bucket."""
            storages = [storage] if storage else config.STORAGE_BACKENDS
            for key in storages:
                try:
                    storage_instance = get_storage(key)
                except RuntimeError:
                    if storage:
                        click.echo(f'Storage {key} does not exist')
                        sys.exit(1)
                    continue

                if isinstance(storage_instance, ReadOnlyStorageMixin):
                    if storage:
                        click.echo(f'Storage {key} is read-only')
                        sys.exit(1)
                    continue

                if isinstance(storage_instance, S3StorageBase):
                    bucket_name = storage_instance._get_current_bucket_name()
                    if storage_instance._bucket_exists(bucket_name):
                        click.echo(f'Storage {key}: bucket {bucket_name} already exists')
                        continue
                    storage_instance._create_bucket(bucket_name)
                    click.echo(f'Storage {key}: bucket {bucket_name} created')
                elif storage:
                    click.echo(f'Storage {key} is not an s3 storage')
                    sys.exit(1)

        s3.add_command(migrate_cli, name='migrate')
        return s3
