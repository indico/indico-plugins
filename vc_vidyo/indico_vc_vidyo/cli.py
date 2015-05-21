# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import sys
from dateutil import rrule

from flask_script import Manager
from terminaltables import AsciiTable

from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus

cli_manager = Manager(usage="Manages the Vidyo plugin")


@cli_manager.option('--status', choices=(b'deleted', b'created'))
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
