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

from datetime import timedelta

from sqlalchemy.sql.expression import cast

from indico.core.db import db
from indico.core.plugins import get_plugin_template_module
from indico.modules.vc.models.vc_rooms import VCRoomEventAssociation, VCRoom, VCRoomStatus
from indico.modules.vc.notifications import _send
from indico.modules.fulltextindexes.models.events import IndexedEvent
from indico.modules.scheduler.tasks.periodic import PeriodicUniqueTask
from indico.util.date_time import now_utc
from indico.util.struct.iterables import committing_iterator
from indico.util.user import retrieve_principal
from indico_vc_vidyo.api import APIException, RoomNotFoundAPIException


def find_old_vidyo_rooms(max_room_event_age):
    """Finds all Vidyo rooms that are:
       - linked to no events
       - linked only to events whose start date precedes today - max_room_event_age days
    """
    recently_used = db.session.query(VCRoom.id).filter(
        VCRoom.type == 'vidyo',
        IndexedEvent.end_date > (now_utc() - timedelta(days=max_room_event_age))
    ).join(VCRoomEventAssociation).join(
        IndexedEvent, IndexedEvent.id == cast(VCRoomEventAssociation.event_id, db.String)
    ).group_by(VCRoom.id)

    # non-deleted rooms with no recent associations
    return VCRoom.find_all(VCRoom.status != VCRoomStatus.deleted, ~VCRoom.id.in_(recently_used))


def notify_moderator(plugin, vc_room):
    """Notifies about the deletion of a Vidyo room from the Vidyo server."""
    user = retrieve_principal(vc_room.data['owner'], allow_groups=False, legacy=False)
    tpl = get_plugin_template_module('emails/remote_deleted.html', plugin=plugin, vc_room=vc_room, event=None,
                                     vc_room_event=None, user=user)
    _send('delete', user, plugin, None, vc_room, tpl.get_subject(), tpl.get_body())


class VidyoCleanupTask(PeriodicUniqueTask):
    """Gets rid of 'old' Vidyo rooms (not used in recent events)"""
    DISABLE_ZODB_HOOK = True

    @property
    def logger(self):
        return self.getLogger()

    def run(self):
        from indico_vc_vidyo.plugin import VidyoPlugin

        plugin = VidyoPlugin.instance  # RuntimeError if not active
        with plugin.plugin_context():

            max_room_event_age = plugin.settings.get('num_days_old')

            self.logger.info('Deleting Vidyo rooms that are not used or linked to events all older than {} days'.format(
                max_room_event_age))

            candidate_rooms = find_old_vidyo_rooms(max_room_event_age)

            self.logger.info('{} rooms found'.format(len(candidate_rooms)))

            for vc_room in committing_iterator(candidate_rooms, n=20):
                try:
                    plugin.delete_room(vc_room, None)
                    self.logger.info('Room {} deleted from Vidyo server'.format(vc_room))
                    notify_moderator(plugin, vc_room)
                    vc_room.status = VCRoomStatus.deleted
                except RoomNotFoundAPIException:
                    self.logger.warning('Room {} had been already deleted from the Vidyo server'.format(vc_room))
                    vc_room.status = VCRoomStatus.deleted
                except APIException:
                    self.logger.exception('Impossible to delete Vidyo room {}'.format(vc_room))
