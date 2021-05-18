# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import current_app
from wtforms.fields.core import BooleanField
from wtforms.fields.html5 import IntegerField, URLField
from wtforms.validators import URL, DataRequired, NumberRange

from indico.core import signals
from indico.core.plugins import PluginCategory
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField, TextListField
from indico.web.forms.widgets import SwitchWidget

from indico_citadel import _
from indico_citadel.backend import LiveSyncCitadelBackend
from indico_citadel.cli import cli
from indico_livesync import LiveSyncPluginBase


class CitadelSettingsForm(IndicoForm):
    search_backend_url = URLField(_('Citadel URL'), [DataRequired(), URL(require_tld=False)],
                                  description=_('The URL of the Citadel server'))
    search_backend_token = IndicoPasswordField(_('Citadel API token'), [DataRequired()], toggle=True,
                                               description=_('The authentication token to access Citadel'))
    file_extensions = TextListField(_('File extensions'),
                                    description=_('File extensions to upload for full-text search'))
    max_file_size = IntegerField(_('Max. file size'),
                                 [DataRequired(), NumberRange(min=1)],
                                 description=_('Maximum size (in MB) to upload for full-text search. Note that '
                                               'increasing this after the initial export will upload all files '
                                               'for indexing that have not been uploaded before during the next queue '
                                               'run, which may take a long time on larger instances. You may want '
                                               'to run a manual upload for the new file size first!'))
    disable_search = BooleanField(_('Disable search'), widget=SwitchWidget(),
                                  description=_('This disables the search integration of the plugin. When this option '
                                                'is used, the internal Indico search interface will be used. This may '
                                                'be useful when you are still running a larger initial export and do '
                                                'not want people to get incomplete search results during that time.'))


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
        'file_extensions': [
            'key', 'odp', 'pps', 'ppt', 'pptx', 'ods', 'xls', 'xlsm', 'xlsx', 'doc', 'docx', 'odt', 'pdf', 'rtf',
            'tex', 'txt', 'wdp'
        ],
        'max_file_size': 10,
        'disable_search': False,
    }
    backend_classes = {'citadel': LiveSyncCitadelBackend}

    def init(self):
        super().init()
        self.connect(signals.get_search_providers, self.get_search_providers)
        self.connect(signals.plugin.cli, self._extend_indico_cli)

    def _is_configured(self):
        return bool(self.settings.get('search_backend_url')) and bool(self.settings.get('search_backend_token'))

    def get_search_providers(self, sender, **kwargs):
        from indico_citadel.search import CitadelProvider
        if current_app.config['TESTING'] or (not self.settings.get('disable_search') and self._is_configured()):
            return CitadelProvider

    def _extend_indico_cli(self, sender, **kwargs):
        return cli
