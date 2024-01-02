# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import os
import sys
import time
import traceback

import click

from indico.cli.core import cli_group
from indico.core.db import db
from indico.util.console import cformat

from indico_citadel.models.id_map import CitadelIdMap
from indico_livesync.models.agents import LiveSyncAgent


@cli_group(name='citadel')
def cli():
    """Manage the Citadel plugin."""


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Upload even if it has already been done once.')
@click.option('--retry', '-r', is_flag=True, help='Restart automatically after a failure')
@click.option('--batch', type=int, default=1000, show_default=True, metavar='N',
              help='The amount of records yielded per upload batch.')
@click.option('--max-size', type=int, metavar='SIZE',
              help='The max size (in MB) of files to upload. Defaults to the size from the plugin settings.')
def upload(batch, force, max_size, retry):
    """Upload file contents for full text search."""
    agent = LiveSyncAgent.query.filter(LiveSyncAgent.backend_name == 'citadel').first()
    if agent is None:
        print('No citadel livesync agent found')
        return
    if not CitadelIdMap.query.has_rows():
        print('It looks like you did not export any data to Citadel yet.')
        print(cformat('To do so, run %{yellow!}indico livesync initial-export {}%{reset}').format(agent.id))
        return

    backend = agent.create_backend()
    if not backend.is_configured():
        print('Citadel is not properly configured.')
        return

    initial = not agent.settings.get('file_upload_done')
    try:
        total, errors, aborted = backend.run_export_files(batch, force, max_size=max_size, initial=initial)
    except Exception:
        if not retry:
            raise
        traceback.print_exc()
        print('Restarting in 2 seconds\a')
        time.sleep(2)
        os.execl(sys.argv[0], *sys.argv)  # noqa: S606
        return  # exec doesn't return but just in case...

    if not errors and not aborted:
        print(f'{total} files uploaded')
        if max_size is None:
            backend.set_initial_file_upload_state(True)
            db.session.commit()
        else:
            print('Max size was set; not enabling queue runs.')
    else:
        if aborted:
            print('Upload aborted')
        print(f'{total} files processed, {errors} failed')
        print('Please re-run this script; queue runs will remain disabled for now')
