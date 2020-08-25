# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import URL, DataRequired, Optional

from indico.web.forms.base import IndicoForm

from indico_livesync import LiveSyncPluginBase
from indico_livesync_citadel import _
from indico_livesync_citadel.backend import LiveSyncCitadelBackend
from indico_livesync_citadel.blueprint import blueprint


class LiveSyncCitadelSettingsForm(IndicoForm):
    search_backend_url = URLField(_('Search backend URL'), [DataRequired(), URL()],
                                  description=_('The URL of the search backend'))
    search_backend_token = StringField(_('Search backend token'), [DataRequired()],
                                       description=_('Authentication token for the search backend'))
    search_owner_role = StringField(_('Search owner role'), [DataRequired()],
                                    description=_('The role set on every synced object. This allows the members '
                                                  'with that role to perform CRUD operations on the backend and '
                                                  'synced objects.'))
    tika_server = URLField(_('Tika server URL'), [Optional(), URL()], description=_('The URL of the tika server'))


class LiveSyncCitadelPlugin(LiveSyncPluginBase):
    """LiveSync Citadel

    Provides the agent for LiveSync Citadel
    """

    configurable = True
    settings_form = LiveSyncCitadelSettingsForm
    default_settings = {'search_backend_url': '', 'search_backend_token': '', 'search_owner_role': '',
                        'tika_server': ''}
    backend_classes = {'livesync_citadel': LiveSyncCitadelBackend}

    def get_blueprints(self):
        return blueprint
