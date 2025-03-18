# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2025 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from operator import attrgetter

import click
from sqlalchemy.orm.attributes import flag_modified
from terminaltables import AsciiTable

from indico.cli.core import cli_group
from indico.core.db import db
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus
from indico.util.console import verbose_iterator


@cli_group(name='zoom')
def cli():
    """Manage the Zoom plugin."""


@cli.command()
@click.option('--status', type=click.Choice(['deleted', 'created']))
def meetings(status=None):
    """Lists all Zoom meetings"""

    room_query = VCRoom.query.filter_by(type='zoom')
    table_data = [['ID', 'Name', 'Status', 'Zoom ID']]

    if status:
        room_query = room_query.filter(VCRoom.status == VCRoomStatus.get(status))

    table_data.extend([str(room.id), room.name, room.status.name, str(room.data['zoom_id'])] for room in room_query)

    table = AsciiTable(table_data)
    for col in (0, 3, 4):
        table.justify_columns[col] = 'right'
    print(table.table)


@cli.command()
def fix_ids():
    """Fixes Zoom IDs stored as strings.

    This ensures Zoom webhooks correctly work for those meetings.
    """

    res = VCRoom.query.filter(VCRoom.type == 'zoom', db.func.jsonb_typeof(VCRoom.data['zoom_id']) == 'string').all()
    for vcr in verbose_iterator(res, len(res), get_id=attrgetter('id'), get_title=lambda x: x.data['zoom_id'],
                                print_total_time=True):
        assert str(int(vcr.data['zoom_id'])) == vcr.data['zoom_id']
        vcr.data['zoom_id'] = int(vcr.data['zoom_id'])
        flag_modified(vcr, 'data')

    db.session.commit()
