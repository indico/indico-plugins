# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import click

from indico.cli.core import cli_group
from indico.core.db import db
from indico.util.console import cformat

from indico_citadel.models.search_id_map import CitadelSearchAppIdMap
from indico_livesync.models.agents import LiveSyncAgent


@cli_group(name='citadel')
def cli():
    """Manage the Citadel plugin."""


@cli.command()
@click.option('--force', is_flag=True, help="Upload even if it has already been done once.")
@click.option('--batch', type=int, help="The amount of records yielded per upload batch.")
def upload(batch, force):
    """Upload the citadel specific attachment files for context extraction"""
    agent = LiveSyncAgent.query.filter(LiveSyncAgent.backend_name == 'citadel').first()
    if agent is None:
        print('No citadel livesync agent found')
        return
    if not CitadelSearchAppIdMap.query.has_rows():
        print('It looks like you did not export any data to Citadel yet.')
        print(cformat('To do so, run %{yellow!}indico livesync initial-export {}%{reset}').format(agent.id))
        print('In case your database is completely empty, use `--force` to skip this check.')
        return
    backend = agent.create_backend()
    backend.run_export_files(batch, force)
    agent.initial_data_exported = True
    db.session.commit()
