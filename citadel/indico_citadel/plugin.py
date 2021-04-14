# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import URL, DataRequired

from indico.core import signals
from indico.core.plugins import PluginCategory
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField, TextListField

from indico_citadel import _
from indico_citadel.backend import LiveSyncCitadelBackend
from indico_citadel.cli import cli
from indico_livesync import LiveSyncPluginBase


class CitadelSettingsForm(IndicoForm):
    search_backend_url = URLField(_('Citadel URL'), [DataRequired(), URL(require_tld=False)],
                                  description=_('The URL of the Citadel server'))
    search_backend_token = IndicoPasswordField(_('Citadel API token'), [DataRequired()], toggle=True,
                                               description=_('The authentication token to access Citadel'))
    search_owner_role = StringField(_('Search owner role'), [DataRequired()],
                                    description=_('The role set on every synced object. This allows the members '
                                                  'with that role to perform CRUD operations on the backend and '
                                                  'synced objects.'))
    file_extensions = TextListField(_('File extensions'),
                                    description=_('The subset of file extensions that will be selected for indexing'))


class CitadelPlugin(LiveSyncPluginBase):
    """Citadel

    Provides the search/livesync integration with Citadel
    """

    category = PluginCategory.search
    configurable = True
    settings_form = CitadelSettingsForm
    default_settings = {
        'search_backend_url': '',
        'search_backend_token': '',
        'search_owner_role': '',
        'file_extensions': (
            'key', 'odp', 'pps', 'ppt', 'pptx', 'ods', 'xls', 'xlsm', 'xlsx', 'doc', 'docx', 'odt', 'pdf', 'rtf',
            'tex', 'txt', 'wdp'
        )
    }
    backend_classes = {'citadel': LiveSyncCitadelBackend}

    def init(self):
        super().init()
        self.connect(signals.get_search_providers, self.get_search_providers)
        self.connect(signals.plugin.cli, self._extend_indico_cli)

    def get_search_providers(self, sender, **kwargs):
        from indico_citadel.search import CitadelProvider
        return CitadelProvider

    def _extend_indico_cli(self, sender, **kwargs):
        return cli
