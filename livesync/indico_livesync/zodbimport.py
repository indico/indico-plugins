# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

from indico.core.db import db
from indico.util.console import cformat
from indico.util.struct.iterables import committing_iterator
from indico_zodbimport import Importer, convert_to_unicode

from indico_livesync.plugin import LiveSyncPlugin
from indico_livesync.models.agents import LiveSyncAgent


class LiveSyncImporter(Importer):
    plugins = {'livesync'}

    def pre_check(self):
        return self.check_plugin_schema('livesync')

    def has_data(self):
        return LiveSyncAgent.find().count()

    def migrate(self):
        # noinspection PyAttributeOutsideInit
        self.livesync_root = self.zodb_root['plugins']['livesync']._storage
        with LiveSyncPlugin.instance.plugin_context():
            self.migrate_settings()
            self.migrate_agents()
        print cformat('%{cyan!}Note: The old queue is not preserved!%{reset}')

    def migrate_settings(self):
        print cformat('%{white!}migrating settings')
        LiveSyncPlugin.settings.delete_all()
        opts = self.zodb_root['plugins']['livesync']._PluginBase__options
        LiveSyncPlugin.settings.set('excluded_categories',
                                    [{'id': x} for x in opts['excludedCategories']._PluginOption__value])
        db.session.commit()

    def migrate_agents(self):
        print cformat('%{white!}migrating agents')
        for old_agent in committing_iterator(self.livesync_root['agent_manager']._agents.itervalues()):
            if not old_agent._active:
                print cformat('%{yellow}skipping inactive agent {} ({})%{reset}').format(old_agent._id, old_agent._name)
                continue

            agent = LiveSyncAgent(name=convert_to_unicode(old_agent._name), initial_data_exported=True)
            old_agent_class = old_agent.__class__.__name__
            if old_agent_class == 'InvenioBatchUploaderAgent':
                agent.backend_name = 'invenio'
                agent.settings = {
                    'server_url': old_agent._url
                }
            elif old_agent_class == 'CERNSearchUploadAgent':
                agent.backend_name = 'cernsearch'
                agent.settings = {
                    'server_url': old_agent._url,
                    'username': old_agent._username,
                    'password': old_agent._password,
                }
            else:
                print cformat('%{red!}skipping unknown agent type: {}%{reset}').format(old_agent_class)
                continue

            print cformat('- %{cyan}{} ({})').format(agent.name, agent.backend_name)
            db.session.add(agent)
