# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

import re

from suds import WebFault
from suds.client import Client
from suds.transport.https import HttpAuthenticated

from indico_vc_vidyo.api.cache import SudsCache

DEFAULT_CLIENT_TIMEOUT = 30
AUTOMUTE_API_PROFILE = "NoAudioAndVideo"


class APIException(Exception):
    pass


class RoomNotFoundAPIException(APIException):
    pass


def raises_api_error(wrapped):
    def _wrapper(*args, **kwargs):
        try:
            return wrapped(*args, **kwargs)
        except WebFault as err:
            err_msg = err.fault.faultstring
            if err_msg.startswith('Room not found for roomID'):
                raise RoomNotFoundAPIException()
            else:
                raise APIException(err_msg)
    return _wrapper


class ClientBase(object):
    def __init__(self, wsdl, settings):
        transport = HttpAuthenticated(username=settings.get('username'), password=settings.get('password'),
                                      timeout=DEFAULT_CLIENT_TIMEOUT)
        self.client = Client(wsdl, cache=SudsCache(), transport=transport, location=re.sub(r'\?wsdl$', '', wsdl))

    @property
    def soap(self):
        return self.client.service


class UserClient(ClientBase):
    def __init__(self, settings):
        super(UserClient, self).__init__(settings.get('user_api_wsdl'), settings)


class AdminClient(ClientBase):
    def __init__(self, settings):
        super(AdminClient, self).__init__(settings.get('admin_api_wsdl'), settings)

    def create_room_object(self, **kwargs):
        room = self.client.factory.create('Room')

        for key, value in kwargs.iteritems():
            setattr(room, key, value)

        return room

    @raises_api_error
    def find_room(self, extension):
        from indico_vc_vidyo.plugin import VidyoPlugin
        filter_ = self.client.factory.create('Filter')
        filter_.query = extension
        filter_.limit = 40
        filter_.dir = 'DESC'

        target_room = None
        counter = 0

        while True:
            filter_.start = counter*filter_.limit
            rooms = self.soap.getRooms(filter_).room
            for room in rooms:
                if int(room.extension) == int(extension):
                    VidyoPlugin.logger.debug('Room: %s has been found.', room)
                    target_room = room
                    break
                else:
                    VidyoPlugin.logger.debug('Dismissing room extension %s', room.extension)
            if target_room:
                return target_room
            counter += 1

    @raises_api_error
    def get_room(self, vidyo_id):
        return self.soap.getRoom(vidyo_id)

    @raises_api_error
    def add_room(self, room_obj):
        self.soap.addRoom(room_obj)

    @raises_api_error
    def update_room(self, room_id, room_obj):
        self.soap.updateRoom(room_id, room_obj)

    @raises_api_error
    def delete_room(self, room_id):
        self.soap.deleteRoom(room_id)

    @raises_api_error
    def get_automute(self, room_id):
        answer = self.soap.getRoomProfile(room_id)
        if answer:
            return answer.roomProfileName == AUTOMUTE_API_PROFILE
        else:
            return False

    @raises_api_error
    def set_automute(self, room_id, status):
        if status:
            self.soap.setRoomProfile(room_id, AUTOMUTE_API_PROFILE)
        else:
            self.soap.removeRoomProfile(room_id)
