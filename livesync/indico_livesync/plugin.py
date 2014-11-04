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

from indico.core.plugins import IndicoPlugin, wrap_cli_manager

from indico_livesync.cli import cli_manager
from indico_livesync.handler import LiveSyncSignalHandler


class LiveSyncPlugin(IndicoPlugin):
    """LiveSync

    Provides a base for livesync plugins.
    """

    hidden = True

    def init(self):
        super(LiveSyncPlugin, self).init()
        self.agent_classes = {}
        self.signal_handler = LiveSyncSignalHandler(self)

    def add_cli_command(self, manager):
        manager.add_command('livesync', wrap_cli_manager(cli_manager, self))

    def register_agent_class(self, name, agent_class):
        if name in self.agent_classes:
            raise RuntimeError('Duplicate livesync agent: {}'.format(name))
        self.agent_classes[name] = agent_class
