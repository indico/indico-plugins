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

from flask import session, request

from MaKaC.webinterface.rh.conferenceModif import RHConferenceModifBase

from indico_chat.models.chatrooms import ChatroomEventAssociation
from indico_chat.util import is_chat_admin


class RHChatManageEventBase(RHConferenceModifBase):
    def _checkParams(self, params):
        RHConferenceModifBase._checkParams(self, params)
        self.event_id = int(self._conf.id)
        self.event = self._conf

    def _checkProtection(self):
        if not is_chat_admin(session.user):
            RHConferenceModifBase._checkProtection(self)


class RHEventChatroomMixin:
    def _checkParams(self):
        self.event_chatroom = ChatroomEventAssociation.find_one(event_id=self.event_id,
                                                                chatroom_id=request.view_args['chatroom_id'])
        self.chatroom = self.event_chatroom.chatroom
