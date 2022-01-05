# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import click
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus


@cli_group(name='zoom')
def cli():
    """Manage the Zoom plugin."""


@cli.command()
@click.option('--status', type=click.Choice(['deleted', 'created']))
def rooms(status=None):
    """Lists all Zoom rooms"""

    room_query = VCRoom.query.filter_by(type='zoom')
    table_data = [['ID', 'Name', 'Status', 'Zoom ID']]

    if status:
        room_query = room_query.filter(VCRoom.status == VCRoomStatus.get(status))

    for room in room_query:
        table_data.append([str(room.id), room.name, room.status.name, str(room.data['zoom_id'])])

    table = AsciiTable(table_data)
    for col in (0, 3, 4):
        table.justify_columns[col] = 'right'
    print(table.table)
