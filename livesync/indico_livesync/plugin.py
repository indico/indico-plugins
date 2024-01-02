# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms.fields import BooleanField, IntegerField
from wtforms.validators import NumberRange

from indico.core import signals
from indico.core.plugins import IndicoPlugin, PluginCategory
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import MultipleItemsField
from indico.web.forms.widgets import SwitchWidget

from indico_livesync import _
from indico_livesync.blueprint import blueprint
from indico_livesync.cli import cli
from indico_livesync.controllers import extend_plugin_details
from indico_livesync.handler import connect_signals


class SettingsForm(IndicoForm):
    queue_entry_ttl = IntegerField(_('Queue entry TTL'), [NumberRange(min=0)],
                                   description=_('How many days should processed entries be kept in the queue. '
                                                 'The time counts from the creation of the queue entries, so if the '
                                                 'LiveSync task is not running for some time, queue entries may be '
                                                 'deleted during the next run after processing them. Setting it to 0 '
                                                 'disables automatic deletion.'))
    excluded_categories = MultipleItemsField(_('Excluded categories'),
                                             fields=[{'id': 'id', 'caption': _('Category ID'), 'required': True}],
                                             description=_('Changes to objects inside these categories or any of their '
                                                           'subcategories are excluded.'))
    disable_queue_runs = BooleanField(_('Disable queue runs'), widget=SwitchWidget(),
                                      description=_('Disable all scheduled queue runs.'))
    skip_category_changes = BooleanField(_('Skip category changes'), widget=SwitchWidget(),
                                         description=_('Skip category changes when processing the queue. This can be '
                                                       'useful in large instances when there are significant changes '
                                                       'to large categories in order to avoid processing those '
                                                       'immediately.'))


class LiveSyncPlugin(IndicoPlugin):
    """LiveSync

    Provides the basic LiveSync functionality.
    Only useful if a livesync agent plugin is installed, too.
    """
    configurable = True
    settings_form = SettingsForm
    default_settings = {'excluded_categories': [],
                        'queue_entry_ttl': 0,
                        'disable_queue_runs': False,
                        'skip_category_changes': False}
    category = PluginCategory.synchronization

    def init(self):
        super().init()
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
            raise RuntimeError(f'Duplicate livesync backend: {name}')
        self.backend_classes[name] = backend_class

    def _extend_plugin_details(self, plugin, **kwargs):
        if plugin == self:
            return extend_plugin_details()
