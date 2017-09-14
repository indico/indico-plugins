# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.exceptions import Fault
from zeep.transports import Transport

from indico_vc_vidyo.api.cache import ZeepCache


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
        except Fault as err:
            err_msg = err.message
            if err_msg.startswith('Room not found for roomID') or 'Invalid roomID' in err_msg:
                raise RoomNotFoundAPIException()
            else:
                raise APIException(err_msg)
    return _wrapper


class ClientBase(object):
    def __init__(self, wsdl, settings):
        session = Session()
        transport = Transport(session=session, cache=ZeepCache())
        session.auth = HTTPBasicAuth(settings.get('username'), settings.get('password'))
        self.client = Client(wsdl, transport=transport)
        self.factory = self.client.type_factory('ns0')

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
        return self.factory.Room(**kwargs)

    @raises_api_error
    def find_room(self, extension):
        from indico_vc_vidyo.plugin import VidyoPlugin
        filter_ = {
            'query': extension,
            'limit': 40,
            'dir': 'DESC'
        }
        counter = 0

        while True:
            filter_['start'] = counter * filter_['limit']
            response = self.soap.getRooms(filter_)
            if not response.total:
                return None
            for room in response.room:
                if int(room.extension) == int(extension):
                    VidyoPlugin.logger.debug('Room: %s has been found.', room)
                    return room
                else:
                    VidyoPlugin.logger.debug('Dismissing room extension %s', room.extension)
                counter += 1

    @raises_api_error
    def get_room(self, vidyo_id):
        return self.soap.getRoom(roomID=vidyo_id)

    @raises_api_error
    def add_room(self, room_obj):
        self.soap.addRoom(room=room_obj)

    @raises_api_error
    def update_room(self, room_id, room_obj):
        self.soap.updateRoom(roomID=room_id, room=room_obj)

    @raises_api_error
    def delete_room(self, room_id):
        self.soap.deleteRoom(roomID=room_id)

    @raises_api_error
    def get_automute(self, room_id):
        answer = self.soap.getRoomProfile(roomID=room_id)
        if answer:
            return answer.roomProfileName == AUTOMUTE_API_PROFILE
        else:
            return False

    @raises_api_error
    def set_automute(self, room_id, status):
        if status:
            self.soap.setRoomProfile(roomID=room_id, roomProfileName=AUTOMUTE_API_PROFILE)
        else:
            self.soap.removeRoomProfile(roomID=room_id)
