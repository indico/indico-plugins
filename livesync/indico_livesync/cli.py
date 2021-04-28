# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import click
from flask_pluginengine import current_plugin
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.core.db import db
from indico.util.console import cformat

from indico_livesync.models.agents import LiveSyncAgent


@cli_group(name='livesync')
def cli():
    """Manage the LiveSync plugin."""


@cli.command()
def available_backends():
    """Lists the currently available backend types"""
    print('The following LiveSync agents are available:')
    for name, backend in current_plugin.backend_classes.items():
        print(cformat('  - %{white!}{}%{reset}: {} ({})').format(name, backend.title, backend.description))


@cli.command()
def agents():
    """Lists the currently active agents"""
    print('The following LiveSync agents are active:')
    agent_list = LiveSyncAgent.query.order_by(LiveSyncAgent.backend_name, db.func.lower(LiveSyncAgent.name)).all()
    table_data = [['ID', 'Name', 'Backend', 'Queue', 'Status']]
    for agent in agent_list:
        if agent.backend is None:
            backend_title = cformat('%{red!}invalid backend ({})%{reset}').format(agent.backend_name)
            queue_status = 'n/a'
        else:
            backend_title = agent.backend.title
            backend = agent.create_backend()
            queue_allowed, reason = backend.check_queue_status()
            if queue_allowed:
                queue_status = cformat('%{green!}ready%{reset}')
            else:
                queue_status = cformat('%{yellow!}{}%{reset}').format(reason)
        table_data.append([str(agent.id), agent.name, backend_title,
                           str(agent.queue.filter_by(processed=False).count()), queue_status])
    table = AsciiTable(table_data)
    table.justify_columns[3] = 'right'
    print(table.table)
    if not all(a.initial_data_exported for a in agent_list):
        print()
        print("You need to perform the initial data export for some agents.")
        print(cformat("To do so, run "
                      "%{yellow!}indico livesync initial-export %{reset}%{yellow}<agent_id>%{reset} for those agents."))


@cli.command()
@click.argument('agent_id', type=int)
@click.option('--force', '-f', is_flag=True, help="Perform export even if it has already been done once.")
@click.option('--verbose', '-v', is_flag=True, help="Be more verbose (what this does is up to the backend)")
@click.option('--batch', type=int, default=5000, help="The amount of records yielded per export batch.",
              show_default=True, metavar='N')
def initial_export(agent_id, batch, force, verbose):
    """Performs the initial data export for an agent"""
    agent = LiveSyncAgent.get(agent_id)
    if agent is None:
        print('No such agent')
        return
    if agent.backend is None:
        print(cformat('Cannot run agent %{red!}{}%{reset} (backend not found)').format(agent.name))
        return
    print(cformat('Selected agent: %{white!}{}%{reset} ({})').format(agent.name, agent.backend.title))
    if agent.initial_data_exported and not force:
        print('The initial export has already been performed for this agent.')
        print(cformat('To re-run it, use %{yellow!}--force%{reset}'))
        return

    backend = agent.create_backend()
    backend.run_initial_export(batch, force, verbose)
    agent.initial_data_exported = True
    db.session.commit()


@cli.command()
@click.argument('agent_id', type=int, required=False)
@click.option('--force', '-f', is_flag=True, help="Run even if initial export was not done")
@click.option('--verbose', '-v', is_flag=True, help="Be more verbose (what this does is up to the backend)")
def run(agent_id, force, verbose):
    """Runs the livesync agent"""
    if agent_id is None:
        agent_list = LiveSyncAgent.query.all()
    else:
        agent = LiveSyncAgent.get(agent_id)
        if agent is None:
            print('No such agent')
            return
        agent_list = [agent]

    for agent in agent_list:
        if agent.backend is None:
            print(cformat('Skipping agent: %{red!}{}%{reset} (backend not found)').format(agent.name))
            continue
        backend = agent.create_backend()
        queue_allowed, reason = backend.check_queue_status()
        if not queue_allowed and not force:
            print(cformat('Skipping agent: %{red!}{}%{reset} ({})').format(agent.name, reason))
            continue
        print(cformat('Running agent: %{white!}{}%{reset}').format(agent.name))
        try:
            backend.run(verbose)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
