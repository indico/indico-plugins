# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import click
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus


@cli_group(name='vidyo')
def cli():
    """Manage the Vidyo plugin."""


@cli.command()
@click.option('--status', type=click.Choice(['deleted', 'created']))
def rooms(status=None):
    """Lists all Vidyo rooms"""

    room_query = VCRoom.find(type='vidyo')
    table_data = [['ID', 'Name', 'Status', 'Vidyo ID', 'Extension']]

    if status:
        room_query = room_query.filter(VCRoom.status == VCRoomStatus.get(status))

    for room in room_query:
        table_data.append([unicode(room.id), room.name, room.status.name,
                           unicode(room.data['vidyo_id']), unicode(room.vidyo_extension.extension)])

    table = AsciiTable(table_data)
    for col in (0, 3, 4):
        table.justify_columns[col] = 'right'
    print table.table
