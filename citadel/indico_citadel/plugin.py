# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine.plugin import render_plugin_template
from wtforms.fields import BooleanField, IntegerField, URLField
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
    num_threads_records = IntegerField(_('Parallel threads (records)'), [NumberRange(min=1, max=500)],
                                       description=_('Number of threads to use when uploading records.'))
    num_threads_records_initial = IntegerField(_('Parallel threads (records, initial export)'),
                                               [NumberRange(min=1, max=500)],
                                               description=_('Number of threads to use when uploading records during '
                                                             'the initial export.'))
    num_threads_files = IntegerField(_('Parallel threads (files)'), [NumberRange(min=1, max=500)],
                                     description=_('Number of threads to use when uploading files.'))
    num_threads_files_initial = IntegerField(_('Parallel threads (files, initial export)'),
                                             [NumberRange(min=1, max=500)],
                                             description=_('Number of threads to use when uploading files during '
                                                           'the initial export.'))
    disable_search = BooleanField(_('Disable search'), widget=SwitchWidget(),
                                  description=_('This disables the search integration of the plugin. When this option '
                                                'is used, the internal Indico search interface will be used. This may '
                                                'be useful when you are still running a larger initial export and do '
                                                'not want people to get incomplete search results during that time.'))
    large_category_warning_threshold = IntegerField(_('Large Category Warning Threshold'),
                                                    [NumberRange(min=0)],
                                                    description=_('Displays a warning to category managers when '
                                                                  'changing the ACL of big categories that would '
                                                                  'result in sending a large amount of data to '
                                                                  'the Citadel server. You can set the threshold '
                                                                  'to 0 to suppress this warning.'))


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
        'num_threads_records': 5,
        'num_threads_records_initial': 25,
        'num_threads_files': 5,
        'num_threads_files_initial': 25,
        'disable_search': False,
        'large_category_warning_threshold': 0,
    }
    backend_classes = {'citadel': LiveSyncCitadelBackend}

    def init(self):
        super().init()
        self.connect(signals.core.get_search_providers, self.get_search_providers)
        self.connect(signals.plugin.cli, self._extend_indico_cli)
        self.template_hook('category-protection-page', self._check_event_categories)

    def get_search_providers(self, sender, **kwargs):
        from indico_citadel.search import CitadelProvider
        return CitadelProvider

    def _extend_indico_cli(self, sender, **kwargs):
        return cli

    def _check_event_categories(self, category):
        threshold = self.settings.get('large_category_warning_threshold')
        if threshold and category.deep_events_count > threshold:
            return render_plugin_template('event_category_warning.html')
