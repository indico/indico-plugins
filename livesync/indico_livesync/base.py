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

from flask_pluginengine import depends, trim_docstring

from indico.core.plugins import IndicoPlugin
from indico.util.decorators import classproperty

from indico_livesync.plugin import LiveSyncPlugin


@depends('livesync')
class LiveSyncPluginBase(IndicoPlugin):
    """Base class for livesync plugins"""

    #: dict containing the agent(s) provided by the plugin; the keys are unique identifiers
    agent_classes = None

    def init(self):
        super(LiveSyncPluginBase, self).init()
        for name, agent_class in self.agent_classes.iteritems():
            assert agent_class.plugin is None
            agent_class.plugin = type(self)
            LiveSyncPlugin.instance.register_agent_class(name, agent_class)


class LiveSyncAgentBase(object):
    """Base class for livesync agents"""

    #: the plugin containing the agent
    plugin = None  # set automatically when the agent is registered

    @classproperty
    @classmethod
    def title(cls):
        parts = trim_docstring(cls.__doc__).split('\n', 1)
        return parts[0].strip()

    @classproperty
    @classmethod
    def description(cls):
        parts = trim_docstring(cls.__doc__).split('\n', 1)
        try:
            return parts[1].strip()
        except IndexError:
            return 'no description available'
