# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import time

import click

from indico.cli.core import cli_group
from indico.core.config import config
from indico.core.db import db
from indico.util.console import cformat

from indico_citadel.models.search_id_map import CitadelSearchAppIdMap
from indico_livesync.models.agents import LiveSyncAgent


@cli_group(name='citadel')
def cli():
    """Manage the Citadel plugin."""


@cli.command()
@click.option('--force', is_flag=True, help="Upload even if it has already been done once.")
@click.option('--batch', type=int, default=1000, help="The amount of records yielded per upload batch.",
              show_default=True, metavar='N')
def upload(batch, force):
    """Upload file contents for full text search."""
    agent = LiveSyncAgent.query.filter(LiveSyncAgent.backend_name == 'citadel').first()
    if agent is None:
        print('No citadel livesync agent found')
        return
    if not CitadelSearchAppIdMap.query.has_rows():
        print('It looks like you did not export any data to Citadel yet.')
        print(cformat('To do so, run %{yellow!}indico livesync initial-export {}%{reset}').format(agent.id))
        return
    backend = agent.create_backend()
    backend.run_export_files(batch, force)
    backend.set_initial_file_upload_state(True)
    db.session.commit()


@cli.command()
def reset():
    """Reset all citadel-related data in Indico."""
    agent = LiveSyncAgent.query.filter(LiveSyncAgent.backend_name == 'citadel').first()
    if agent is None:
        print('No citadel livesync agent found')
        return
    if not CitadelSearchAppIdMap.query.has_rows():
        print('It looks like you did not export any data to Citadel yet, so there is nothing to reset')
        return

    print(cformat('%{yellow!}!!! %{red!}DANGER %{yellow!}!!!%{reset}'))
    print(cformat('%{yellow!}This command should only be used if the data on citadel has been deleted%{reset}'))
    print(cformat('%{yellow!}and you want to re-export everything.%{reset}'))
    print(cformat('%{yellow!}After resetting you need to perform a new initial export.%{reset}'))
    click.confirm(click.style('Do you really want to reset the local citadel data?', fg='red', bold=True),
                  default=False, abort=True)
    if not config.DEBUG:
        click.confirm(click.style('Are you absolutely sure?', fg='red', bold=True), default=False, abort=True)
        for i in range(5):
            print(cformat('\rResetting in %{white!}{}%{reset}s (CTRL+C to abort)').format(5 - i), end='')
            time.sleep(1)
        print('')
    print('Resetting initial data export & file upload state...')
    agent.initial_data_exported = False
    agent.create_backend().set_initial_file_upload_state(False)
    print('Emptying queue...')
    agent.queue.delete()
    print('Deleting Citadel ID mappings...')
    CitadelSearchAppIdMap.query.delete()
    db.session.commit()
    print(cformat('Reset complete; run %{green!}indico livesync initial-export {}%{reset} for a new export')
          .format(agent.id))
