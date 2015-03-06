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

from indico.core.db import db, DBMgr
from indico.core.db.sqlalchemy.util.session import update_session_options
from indico.modules.scheduler import Client
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus

from indico_vc_vidyo.task import VidyoCleanupTask

cli_manager = Manager(usage="Manages the Vidyo plugin")


@cli_manager.command
@cli_manager.option('--deleted', action='store_true')
@cli_manager.option('--created', action='store_true')
def rooms(deleted=False, created=False):
    """Lists all Vidyo rooms"""

    room_query = VCRoom.find(type='vidyo')
    table_data = [['ID', 'Name', 'Status', 'Vidyo ID', 'Extension']]

    if deleted:
        room_query = room_query.filter(VCRoom.status == VCRoomStatus.deleted)
    if created:
        room_query = room_query.filter(VCRoom.status == VCRoomStatus.created)

    for room in room_query:
        table_data.append([unicode(room.id), room.name, room.status.name,
                           unicode(room.data['vidyo_id']), unicode(room.vidyo_extension.extension)])

    table = AsciiTable(table_data)
    table.justify_columns[4] = 'right'
    print table.table


@cli_manager.command
def create_task(interval):
    """Creates a Vidyo cleanup task running every N days"""
    update_session_options(db)
    try:
        interval = int(interval)
        if interval < 1:
            raise ValueError
    except ValueError:
        print 'Invalid interval, must be a number >=1'
        sys.exit(1)
    with DBMgr.getInstance().global_connection(commit=True):
        Client().enqueue(VidyoCleanupTask(rrule.DAILY, interval=interval))
    print 'Task created'
