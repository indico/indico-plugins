# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import click

from indico.cli.core import cli_group

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
    backend = agent.create_backend()
    backend.run_export_files(batch, force)