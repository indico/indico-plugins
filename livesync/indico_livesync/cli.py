# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import time

import click
from flask_pluginengine import current_plugin
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.core.config import config
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

    backend = agent.create_backend()
    if not backend.is_configured():
        print(cformat('Agent %{red!}{}%{reset} is not properly configured').format(agent.name))
        return

    if agent.initial_data_exported and not force:
        print('The initial export has already been performed for this agent.')
        print(cformat('To re-run it, use %{yellow!}--force%{reset}'))
        return

    if not backend.run_initial_export(batch, force, verbose):
        print('The initial export failed; not marking it as done')
        return

    agent.initial_data_exported = True
    db.session.commit()


@cli.command()
@click.argument('agent_id', type=int, required=False)
@click.option('--force', '-f', is_flag=True, help="Run even if initial export was not done")
@click.option('--verbose', '-v', is_flag=True, help="Be more verbose (what this does is up to the backend)")
def run(agent_id, force, verbose):
    """Runs the livesync agent"""
    from indico_livesync.plugin import LiveSyncPlugin
    if LiveSyncPlugin.settings.get('disable_queue_runs'):
        print(cformat('%{yellow!}Queue runs are disabled%{reset}'))
        return

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
            backend.run(verbose, from_cli=True)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


@cli.command()
@click.argument('agent_id', type=int)
def reset(agent_id):
    """Performs the initial data export for an agent"""
    agent = LiveSyncAgent.get(agent_id)
    if agent is None:
        print('No such agent')
        return

    if agent.backend is None:
        print(cformat('Cannot run agent %{red!}{}%{reset} (backend not found)').format(agent.name))
        return

    backend = agent.create_backend()
    reset_allowed, message = backend.check_reset_status()

    if not reset_allowed:
        print(f'Resetting is not possible: {message}')
        return

    print(cformat('Selected agent: %{white!}{}%{reset} ({})').format(agent.name, backend.title))
    print(cformat('%{yellow!}!!! %{red!}DANGER %{yellow!}!!!%{reset}'))
    if backend.reset_deletes_indexed_data:
        print(cformat('%{yellow!}This command will delete all indexed data on this backend.%{reset}')
              .format(backend.title))
    else:
        print(cformat('%{yellow!}This command should only be used if the data on this backend '
                      'has been deleted.%{reset}')
              .format(backend.title))
    print(cformat('%{yellow!}After resetting you need to perform a new initial export.%{reset}'))
    click.confirm(click.style('Do you really want to perform the reset?', fg='red', bold=True),
                  default=False, abort=True)
    if not config.DEBUG:
        click.confirm(click.style('Are you absolutely sure?', fg='red', bold=True), default=False, abort=True)
        for i in range(5):
            print(cformat('\rResetting in %{white!}{}%{reset}s (CTRL+C to abort)').format(5 - i), end='')
            time.sleep(1)
        print('')

    backend.reset()
    db.session.commit()
    print(cformat('Reset complete; run %{green!}indico livesync initial-export {}%{reset} for a new export')
          .format(agent.id))
