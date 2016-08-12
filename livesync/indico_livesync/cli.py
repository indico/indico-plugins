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

import transaction
from flask_pluginengine import current_plugin
from flask_script import Manager
from terminaltables import AsciiTable

from indico.core.db import db, DBMgr
from indico.core.db.sqlalchemy.util.session import update_session_options
from indico.modules.events.models.events import Event
from indico.util.console import cformat

from indico_livesync.models.agents import LiveSyncAgent


cli_manager = Manager(usage="Manages LiveSync")


@cli_manager.command
def available_backends():
    """Lists the currently available backend types"""
    print 'The following LiveSync agents are available:'
    for name, backend in current_plugin.backend_classes.iteritems():
        print cformat('  - %{white!}{}%{reset}: {} ({})').format(name, backend.title, backend.description)


@cli_manager.command
def agents():
    """Lists the currently active agents"""
    print 'The following LiveSync agents are active:'
    agent_list = LiveSyncAgent.find().order_by(LiveSyncAgent.backend_name, db.func.lower(LiveSyncAgent.name)).all()
    table_data = [['ID', 'Name', 'Backend', 'Initial Export', 'Queue']]
    for agent in agent_list:
        initial = (cformat('%{green!}done%{reset}') if agent.initial_data_exported else
                   cformat('%{yellow!}pending%{reset}'))
        if agent.backend is None:
            backend_title = cformat('%{red!}invalid backend ({})%{reset}').format(agent.backend_name)
        else:
            backend_title = agent.backend.title
        table_data.append([unicode(agent.id), agent.name, backend_title, initial,
                           unicode(agent.queue.filter_by(processed=False).count())])
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
    if agent.backend is None:
        print cformat('Cannot run agent %{red!}{}%{reset} (backend not found)').format(agent.name)
        return
    print cformat('Selected agent: %{white!}{}%{reset} ({})').format(agent.name, agent.backend.title)
    if agent.initial_data_exported and not force:
        print 'The initial export has already been performed for this agent.'
        print cformat('To re-run it, use %{yellow!}--force%{reset}')
        return

    agent.create_backend().run_initial_export(Event.find(is_deleted=False))
    agent.initial_data_exported = True
    db.session.commit()


@cli_manager.option('agent_id')
@cli_manager.option('--force', action='store_true', help="Run even if initial export was not done")
def run(agent_id, force=False):
    """Runs the livesync agent"""
    update_session_options(db)
    if agent_id is None:
        agent_list = LiveSyncAgent.find_all()
    else:
        agent = LiveSyncAgent.find_first(id=int(agent_id))
        if agent is None:
            print 'No such agent'
            return
        agent_list = [agent]

    for agent in agent_list:
        if agent.backend is None:
            print cformat('Skipping agent: %{red!}{}%{reset} (backend not found)').format(agent.name)
            continue
        if not agent.initial_data_exported and not force:
            print cformat('Skipping agent: %{red!}{}%{reset} (initial export not performed)').format(agent.name)
            continue
        print cformat('Running agent: %{white!}{}%{reset}').format(agent.name)
        with DBMgr.getInstance().global_connection():
            try:
                agent.create_backend().run()
                db.session.commit()
            finally:
                transaction.abort()
