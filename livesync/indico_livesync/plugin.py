# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

from wtforms.fields.html5 import IntegerField
from wtforms.validators import NumberRange

from indico.core import signals
from indico.core.plugins import IndicoPlugin, PluginCategory
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import MultipleItemsField

from indico_livesync import _
from indico_livesync.blueprint import blueprint
from indico_livesync.cli import cli
from indico_livesync.controllers import extend_plugin_details
from indico_livesync.handler import connect_signals


class SettingsForm(IndicoForm):
    queue_entry_ttl = IntegerField(_('Queue entry TTL'), [NumberRange(min=0)],
                                   description=_("How many days should processed entries be kept in the queue. "
                                                 "The time counts from the creation of the queue entries, so if the "
                                                 "LiveSync task is not running for some time, queue entries may be "
                                                 "deleted during the next run after processing them. Setting it to 0 "
                                                 "disables automatic deletion."))
    excluded_categories = MultipleItemsField(_('Excluded categories'),
                                             fields=[{'id': 'id', 'caption': _("Category ID"), 'required': True}],
                                             description=_("Changes to objects inside these categories or any of their "
                                                           "subcategories are excluded."))


class LiveSyncPlugin(IndicoPlugin):
    """LiveSync

    Provides the basic LiveSync functionality.
    Only useful if a livesync agent plugin is installed, too.
    """
    configurable = True
    settings_form = SettingsForm
    default_settings = {'excluded_categories': [],
                        'queue_entry_ttl': 0}
    category = PluginCategory.synchronization

    def init(self):
        super(LiveSyncPlugin, self).init()
        self.backend_classes = {}
        connect_signals(self)
        self.connect(signals.plugin.cli, self._extend_indico_cli)
        self.template_hook('plugin-details', self._extend_plugin_details)

    def get_blueprints(self):
        return blueprint

    def _extend_indico_cli(self, sender, **kwargs):
        return cli

    def register_backend_class(self, name, backend_class):
        if name in self.backend_classes:
            raise RuntimeError('Duplicate livesync backend: {}'.format(name))
        self.backend_classes[name] = backend_class

    def _extend_plugin_details(self, plugin, **kwargs):
        if plugin == self:
            return extend_plugin_details()
