# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import click
from flask_pluginengine import current_plugin
from sqlalchemy.orm import subqueryload
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.core.db import db
from indico.modules.categories import Category
from indico.modules.categories.models.principals import CategoryPrincipal
from indico.util.console import cformat

from indico_livesync.initial import (apply_acl_entry_strategy, query_attachments, query_contributions, query_events,
                                     query_notes)
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
    table_data = [['ID', 'Name', 'Backend', 'Initial Export', 'Queue']]
    for agent in agent_list:
        initial = (cformat('%{green!}done%{reset}') if agent.initial_data_exported else
                   cformat('%{yellow!}pending%{reset}'))
        if agent.backend is None:
            backend_title = cformat('%{red!}invalid backend ({})%{reset}').format(agent.backend_name)
        else:
            backend_title = agent.backend.title
        table_data.append([str(agent.id), agent.name, backend_title, initial,
                           str(agent.queue.filter_by(processed=False).count())])
    table = AsciiTable(table_data)
    table.justify_columns[4] = 'right'
    print(table.table)
    if not all(a.initial_data_exported for a in agent_list):
        print()
        print("You need to perform the initial data export for some agents.")
        print(cformat("To do so, run "
                      "%{yellow!}indico livesync initial-export %{reset}%{yellow}<agent_id>%{reset} for those agents."))


@cli.command()
@click.argument('agent_id', type=int)
@click.option('--force', is_flag=True, help="Perform export even if it has already been done once.")
def initial_export(agent_id, force):
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

    Category.allow_relationship_preloading = True
    Category.preload_relationships(Category.query, 'acl_entries',
                                   strategy=lambda rel: apply_acl_entry_strategy(subqueryload(rel), CategoryPrincipal))
    _category_cache = Category.query.all()  # noqa: F841

    backend = agent.create_backend()
    events = query_events()
    backend.run_initial_export(events.yield_per(5000), events.count())
    contributions = query_contributions()
    backend.run_initial_export(contributions.yield_per(5000), contributions.count())
    attachments = query_attachments()
    backend.run_initial_export(attachments.yield_per(5000), attachments.count())
    notes = query_notes()
    backend.run_initial_export(notes.yield_per(5000), notes.count())
    agent.initial_data_exported = True
    db.session.commit()


@cli.command()
@click.argument('agent_id', type=int, required=False)
@click.option('--force', is_flag=True, help="Run even if initial export was not done")
def run(agent_id, force=False):
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
        if not agent.initial_data_exported and not force:
            print(cformat('Skipping agent: %{red!}{}%{reset} (initial export not performed)').format(agent.name))
            continue
        print(cformat('Running agent: %{white!}{}%{reset}').format(agent.name))
        try:
            agent.create_backend().run()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
