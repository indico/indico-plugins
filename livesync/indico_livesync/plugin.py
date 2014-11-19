# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from flask import request

from wtforms.validators import NumberRange
from wtforms.fields.html5 import IntegerField

from indico.core.plugins import IndicoPlugin, wrap_cli_manager
from indico.core.plugins.views import WPPlugins
from indico.util.i18n import _
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import MultipleItemsField

from indico_livesync.blueprint import blueprint
from indico_livesync.cli import cli_manager
from indico_livesync.controllers import extend_plugin_details
from indico_livesync.handler import connect_signals


class SettingsForm(IndicoForm):
    queue_entry_ttl = IntegerField(_('Queue entry TTL'), [NumberRange(min=0)],
                                   description=_("How many days should processed entries be kept in the queue. "
                                                 "The time counts from the creation of the queue entries, so if the "
                                                 "LiveSync task is not running for some time, queue entries may be "
                                                 "deleted during the next run after processing them. Setting it to 0 "
                                                 "disables automatic deletion."))
    excluded_categories = MultipleItemsField(_('Excluded categories'), fields=(('id', _('Category ID')),),
                                             description=_("Changes to objects inside these categories or any of their "
                                                           "subcategories are excluded."))


class LiveSyncPlugin(IndicoPlugin):
    """LiveSync

    Provides the basic LiveSync functionality.
    Only useful if a livesync agent plugin is installed, too.
    """

    settings_form = SettingsForm
    default_settings = {'excluded_categories': [],
                        'queue_entry_ttl': 0}

    def init(self):
        super(LiveSyncPlugin, self).init()
        self.agent_classes = {}
        connect_signals(self)
        self.template_hook('plugin-details', self._extend_plugin_details)
        self.inject_js('livesync_admin_js', WPPlugins, subclasses=False,
                       condition=lambda: request.view_args.get('plugin') == self.name)

    def get_blueprints(self):
        return blueprint

    def register_assets(self):
        self.register_js_bundle('livesync_admin_js', 'js/livesync_admin.js')

    def add_cli_command(self, manager):
        manager.add_command('livesync', wrap_cli_manager(cli_manager, self))

    def register_agent_class(self, name, agent_class):
        if name in self.agent_classes:
            raise RuntimeError('Duplicate livesync agent: {}'.format(name))
        self.agent_classes[name] = agent_class

    def _extend_plugin_details(self, plugin, **kwargs):
        if plugin == self:
            return extend_plugin_details()
