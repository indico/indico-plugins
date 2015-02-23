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

import re

from indico.core.config import Config
from indico.core.db import db
from indico.util.console import cformat
from indico.util.struct.iterables import committing_iterator

from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus, VCRoomLinkType
from indico_vc_vidyo.models.vidyo_extensions import VidyoExtension
from indico_vc_vidyo.plugin import VidyoPlugin
from indico_zodbimport import Importer


LINKED_ID_RE = re.compile(r'.*[st](\w+)$')
MAP_LINK_TYPES = {
    'event': 'event',
    'contribution': 'contribution',
    'session': 'block'
}


def extract_id(full_id):
    return LINKED_ID_RE.match(full_id).group(1).replace('l', ':')


class VidyoImporter(Importer):
    plugins = {'vc_vidyo'}

    def pre_check(self):
        return self.check_plugin_schema('vc_vidyo')

    def has_data(self):
        return VCRoom.find(type='vidyo').count() or VidyoExtension.find().count()

    def migrate(self):
        self.migrate_settings()

        self.booking_root = self.zodb_root['catalog']['BookingsByVidyoRoomIndex']._fwd_index
        with VidyoPlugin.instance.plugin_context():
            for booking_id, bookings in committing_iterator(self.booking_root.iteritems()):
                all_bookings = list(bookings)
                vc_room = self.migrate_vidyo_room(all_bookings[0])
                self.migrate_event_bookings(vc_room, all_bookings)

    def migrate_settings(self):
        # TODO: migrate settings
        pass

    def migrate_vidyo_room(self, booking):
        booking_params = booking._bookingParams
        vc_room = VCRoom(created_by_id=Config.getInstance().getJanitorUserId())
        vc_room.type = 'vidyo'
        vc_room.status = VCRoomStatus.created if booking._created else VCRoomStatus.deleted
        vc_room.name = booking_params['roomName']
        vc_room.data = {
            'description': booking_params['roomDescription'],
            'room_pin': booking._pin,
            'display_pin': booking_params['displayPin'],
            'moderation_pin': booking._moderatorPin,
            'show_phone_numbers': booking_params['displayPhoneNumbers'],
            'show_autojoin': booking_params['displayURL'],
            'vidyo_id': booking._roomId,
            'url': booking._url,
            'show': not booking._hidden,
            'owner': ('Avatar', booking._owner.id),
            'owner_identity': booking._ownerVidyoAccount,
            'auto_mute': booking_params.get('autoMute', True)
        }
        db.session.add(vc_room)
        db.session.flush()
        vidyo_ext = VidyoExtension(vc_room_id=vc_room.id, value=booking._extension)

        db.session.add(vidyo_ext)

        print cformat('- %{cyan}{}%{reset} [%{yellow!}{}%{reset}]').format(vc_room.name, booking._roomId)
        return vc_room

    def migrate_event_bookings(self, vc_room, bookings):
        for booking in bookings:
            event_vc_room = VCRoomEventAssociation(
                event_id=booking._conf.id,
                vc_room=vc_room,
                link_type=(VCRoomLinkType.get(MAP_LINK_TYPES[booking._linkVideoType])
                           if booking._linkVideoType else VCRoomLinkType.event),
                link_id=(extract_id(booking._linkVideoId) if booking._linkVideoType not in ('event', None) else None)
            )
            db.session.add(event_vc_room)
            print cformat('  + %{red!}{}%{reset} [%{yellow}{}%{reset}]').format(
                booking._conf.id, booking._linkVideoType)
