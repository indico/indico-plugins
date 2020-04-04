

from __future__ import unicode_literals

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

    room_query = VCRoom.find(type='zoom')
    table_data = [['ID', 'Name', 'Status', 'Zoom ID', 'Meeting']]

    if status:
        room_query = room_query.filter(VCRoom.status == VCRoomStatus.get(status))

    for room in room_query:
        table_data.append([unicode(room.id), room.name, room.status.name,
                           unicode(room.data['zoom_id']), unicode(room.zoom_meeting.meeting)])

    table = AsciiTable(table_data)
    for col in (0, 3, 4):
        table.justify_columns[col] = 'right'
    print table.table
