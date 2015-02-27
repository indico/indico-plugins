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
from indico_zodbimport import Importer, option_value, convert_principal_list, convert_to_unicode

from indico_vc_vidyo.models.vidyo_extensions import VidyoExtension
from indico_vc_vidyo.plugin import VidyoPlugin


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
        self.booking_root = self.zodb_root['catalog']['cs_bookingmanager_conference']._tree
        self.migrate_settings()
        self.migrate_event_bookings()

    def migrate_event_bookings(self):
        with VidyoPlugin.instance.plugin_context():
            for event_id, csbm in committing_iterator(self.booking_root.iteritems(), n=1000):
                for bid, booking in csbm._bookings.iteritems():
                    if booking._type == 'Vidyo':
                        vc_room = VCRoom.find(VidyoExtension.value == booking._extension).join(VidyoExtension).first()
                        if not vc_room:
                            vc_room = self.migrate_vidyo_room(booking)
                        self.migrate_event_booking(vc_room, booking)

    def migrate_settings(self):
        print cformat('%{white!}migrating settings')
        VidyoPlugin.settings.delete_all()
        opts = self.zodb_root['plugins']['Collaboration']._PluginType__plugins['Vidyo']._PluginBase__options
        VidyoPlugin.settings.set('managers', convert_principal_list(opts['admins']))
        VidyoPlugin.settings.set('acl', convert_principal_list(opts['AuthorisedUsersGroups']))
        VidyoPlugin.settings.set('authenticators', ', '.join(map(convert_to_unicode,
                                                                 option_value(opts['authenticatorList']))))
        settings_map = {
            'adminAPIURL': 'admin_api_wsdl',
            'userAPIURL': 'user_api_wsdl',
            'prefix': 'indico_room_prefix',
            'indicoGroup': 'room_group_name',
            'phoneNumbers': 'vidyo_phone_link',
            'maxDaysBeforeClean': 'num_days_old',
            'indicoUsername': 'username',
            'indicoPassword': 'password',
            'contactSupport': 'support_email',
            'cleanWarningAmount': 'max_rooms_warning',
            'additionalEmails': 'notification_emails'
        }
        for old, new in settings_map.iteritems():
            value = option_value(opts[old])
            if old == 'prefix':
                value = int(value)
            elif old == 'phoneNumbers':
                match = next((re.search(r'https?://[^"]+', convert_to_unicode(v)) for v in value), None)
                if match is None:
                    continue
                value = match.group(0)
            elif old == 'additionalEmails':
                value = list(set(value) | {x.getEmail() for x in option_value(opts['admins'])})
            VidyoPlugin.settings.set(new, value)
        db.session.commit()

    def migrate_vidyo_room(self, booking):
        booking_params = booking._bookingParams
        vc_room = VCRoom(created_by_id=Config.getInstance().getJanitorUserId())
        vc_room.type = 'vidyo'
        vc_room.status = VCRoomStatus.created if booking._created else VCRoomStatus.deleted
        vc_room.name = booking_params['roomName']
        vc_room.show = not booking._hidden
        vc_room.data = {
            'description': booking_params['roomDescription'],
            'room_pin': booking._pin,
            'moderation_pin': booking._moderatorPin,
            'vidyo_id': booking._roomId,
            'url': booking._url,
            'owner': ('Avatar', booking._owner.id),
            'owner_identity': booking._ownerVidyoAccount,
            'auto_mute': booking_params.get('autoMute', True)
        }
        vc_room.modified_dt = booking._modificationDate
        vc_room.created_dt = booking._creationDate

        db.session.add(vc_room)

        vidyo_ext = VidyoExtension(vc_room=vc_room, value=booking._extension)

        db.session.add(vidyo_ext)
        db.session.flush()

        print cformat('%{green}+++%{reset} %{cyan}{}%{reset} [%{yellow!}{}%{reset}]').format(
            vc_room.name, booking._roomId)
        return vc_room

    def migrate_event_booking(self, vc_room, booking):
        ch_idx = self.zodb_root['conferences']
        booking_params = booking._bookingParams

        link_type = (VCRoomLinkType.get(MAP_LINK_TYPES[booking._linkVideoType]) if booking._linkVideoType
                     else VCRoomLinkType.event)

        if booking._conf.id not in ch_idx:
            print cformat(
                "[%{red!}WARNING%{reset}] %{yellow!}{} is linked to event '{}' but the latter seems to have been"
                " deleted. Removing link."
            ).format(vc_room, booking._conf.id)
            return

        if link_type == VCRoomLinkType.event:
            extracted_id = None
        elif not booking._linkVideoId:
            print cformat(
                "[%{red!}WARNING%{reset}] %{yellow!}{} is linked to a {} but no id given%{reset}. Linking to event."
            ).format(vc_room, link_type.name)
            extracted_id = None
            link_type = VCRoomLinkType.event
        else:
            extracted_id = extract_id(booking._linkVideoId)

        event_vc_room = VCRoomEventAssociation(
            event_id=booking._conf.id,
            vc_room=vc_room,
            link_type=link_type,
            link_id=extracted_id
        )
        event_vc_room.data = {
            'show_pin': booking_params['displayPin'],
            'show_phone_numbers': booking_params.get('displayPhoneNumbers', True),
            'show_autojoin': booking_params['displayURL'],
        }

        db.session.add(event_vc_room)
        print cformat('%{green}<->%{reset} %{cyan!}{}%{reset} %{red!}{}%{reset} [%{yellow}{}%{reset}]').format(
            booking._conf.id, booking._roomId, booking._linkVideoType)
