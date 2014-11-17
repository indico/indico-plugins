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

import sys

import transaction
from dateutil import rrule
from flask_pluginengine import current_plugin
from flask_script import Manager
from terminaltables import AsciiTable

from indico.core.db import db, DBMgr
from indico.core.db.sqlalchemy.util.session import update_session_options
from indico.modules.scheduler import Client
from indico.util.console import cformat, conferenceHolderIterator
from MaKaC.conference import ConferenceHolder

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.task import LiveSyncTask


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
        if agent.backend is None:
            backend_title = cformat('%{red!}invalid backend ({})%{reset}').format(agent.backend_name)
        else:
            backend_title = agent.backend.title
        table_data.append([unicode(agent.id), agent.name, backend_title, initial, unicode(agent.queue.count())])
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

    def _iter_events():
        for i, (_, event) in enumerate(conferenceHolderIterator(ConferenceHolder(), deepness='event'), 1):
            yield event
            if i % 1000 == 0:
                # Clean local ZEO cache
                transaction.abort()

    with DBMgr.getInstance().global_connection():
        agent.create_backend().run_initial_export(_iter_events())

    agent.initial_data_exported = True
    db.session.commit()


@cli_manager.command
def run(agent_id=None):
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
        if not agent.initial_data_exported:
            print cformat('Skipping agent: %{red!}{}%{reset} (initial export not performed)').format(agent.name)
            continue
        print cformat('Running agent: %{white!}{}%{reset}').format(agent.name)
        with DBMgr.getInstance().global_connection():
            try:
                agent.create_backend().run()
                db.session.commit()
            finally:
                transaction.abort()


@cli_manager.command
def create_task(interval):
    """Creates a livesync task running every N minutes"""
    update_session_options(db)
    try:
        interval = int(interval)
        if interval < 1:
            raise ValueError
    except ValueError:
        print 'Invalid interval, must be a number >=1'
        sys.exit(1)
    with DBMgr.getInstance().global_connection(commit=True):
        Client().enqueue(LiveSyncTask(rrule.MINUTELY, interval=interval))
    print 'Task created'
