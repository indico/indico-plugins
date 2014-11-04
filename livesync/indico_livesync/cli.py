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

from flask_pluginengine import current_plugin
from flask_script import Manager
from terminaltables import AsciiTable

from indico.core.db import db
from indico.core.db.sqlalchemy.util.session import update_session_options
from indico.util.console import cformat

from indico_livesync.models.agents import LiveSyncAgent


cli_manager = Manager(usage="Manages LiveSync")


@cli_manager.command
def available_agents():
    """Lists the currently available agent types"""
    print 'The following LiveSync agents are available:'
    for name, agent_class in current_plugin.agent_classes.iteritems():
        print cformat('  - %{white!}{}%{reset}: {} ({})').format(name, agent_class.title, agent_class.description)


@cli_manager.command
def agents():
    """Lists the currently active agents"""
    print 'The following LiveSync agents are active:'
    agent_list = LiveSyncAgent.find().order_by(LiveSyncAgent.backend_name, db.func.lower(LiveSyncAgent.name)).all()
    table_data = [['ID', 'Name', 'Backend', 'Initial Export', 'Queue']]
    for agent in agent_list:
        initial = (cformat('%{green!}done%{reset}') if agent.initial_data_exported else
                   cformat('%{yellow!}pending%{reset}'))
        table_data.append([unicode(agent.id), agent.name, agent.backend.title, initial, unicode(agent.queue.count())])
    table = AsciiTable(table_data)
    table.justify_columns[4] = 'right'
    print table.table
    if not all(a.initial_data_exported for a in agent_list):
        print
        print "You need to perform the initial data export for some agents."
        print cformat("To do so, run "
                      "%{yellow!}indico livesync initial_export %{reset}%{yellow}<agent_id>%{reset} for those agents.")


@cli_manager.option('agent_id')
@cli_manager.option('--force', action='store_true')
def initial_export(agent_id, force=False):
    """Performs the initial data export for an agent"""
    update_session_options(db)
    agent = LiveSyncAgent.find_first(id=int(agent_id))
    if agent is None:
        print 'No such agent'
        return
    print cformat('Selected agent: %{white!}{}%{reset} ({})').format(agent.name, agent.backend.title)
    if agent.initial_data_exported and not force:
        print 'The initial export has already been performed for this agent.'
        print cformat('To re-run it, use %{yellow!}--force%{reset}')
        return
    print 'TODO: run initial export'
    agent.initial_data_exported = True
    db.session.commit()


@cli_manager.command
def create_agent(agent_type, name=None):
    """Creates a new agent"""
    update_session_options(db)
    try:
        agent_class = current_plugin.agent_classes[agent_type]
    except KeyError:
        print 'No such agent type'
        return
    # TODO: Prompt for agent type specific settings
    agent = LiveSyncAgent(backend_name=agent_type, name=name or agent_class.title)
    db.session.add(agent)
    db.session.commit()
    print agent


# TODO: delete_agent, update_agent, create_task


@cli_manager.command
def run(agent_id=None):
    if agent_id is None:
        agents = LiveSyncAgent.find_all()
    else:
        agent = LiveSyncAgent.find_first(id=int(agent_id))
        if agent is None:
            print 'No such agent'
            return
        agents = [agent]

    for agent in agents:
        pass  # TODO
