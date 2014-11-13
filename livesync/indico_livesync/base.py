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
from MaKaC.conference import CategoryManager

from indico_livesync.models.queue import LiveSyncQueueEntry
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
    #: the Uploader to use. only needed if run and run_initial_export are not overridden
    uploader = None

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

    def __init__(self, agent, task=None):
        """
        :param agent: a `LiveSyncAgent` instance
        :param task: a `LiveSyncTask` instance if running as a task
        """
        self.agent = agent
        self.task = task
        self.excluded_categories = self._get_excluded_categories()

    def _get_excluded_categories(self):
        todo = {x['id'] for x in LiveSyncPlugin.settings.get('excluded_categories')}
        excluded = set()
        while todo:
            category_id = todo.pop()
            try:
                category = CategoryManager().getById(category_id)
            except KeyError:
                continue
            excluded.add(category.getId())
            todo.update(category.subcategories)
        return excluded

    def _is_entry_excluded(self, entry):
        if entry.type == 'category':
            return entry.category_id in self.excluded_categories
        else:
            obj = entry.object
            if not obj:
                return False
            category = obj.getConference().getOwner() if obj.getConference() else None
            if category:
                return category.getId() in self.excluded_categories
        return False

    def fetch_records(self, count=None):
        query = (self.agent.queue
                 .filter_by(processed=False)
                 .order_by(LiveSyncQueueEntry.timestamp)
                 .limit(count))
        return [entry for entry in query if not self._is_entry_excluded(entry)]

    def run(self):
        """Runs the livesync export"""
        if self.uploader is None:
            raise NotImplementedError

        records = self.fetch_records()
        uploader = self.uploader(self)
        uploader.run(records)

    def run_initial_export(self, events):
        """Runs the initial export.

        This process is expected to take a very long time.

        :param events: iterable of all events in this indico instance
        """
        if self.uploader is None:
            raise NotImplementedError

        uploader = self.uploader(self)
        uploader.run_initial(events)
