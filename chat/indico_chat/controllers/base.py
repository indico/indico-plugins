# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask import request, session

from indico.modules.events.management.controllers import RHManageEventBase

from indico_chat.models.chatrooms import ChatroomEventAssociation
from indico_chat.util import is_chat_admin


class RHChatManageEventBase(RHManageEventBase):
    def _check_access(self):
        if not is_chat_admin(session.user):
            RHManageEventBase._check_access(self)


class RHEventChatroomMixin:
    def _process_args(self):
        self.event_chatroom = (ChatroomEventAssociation.query.with_parent(self.event)
                               .filter_by(chatroom_id=request.view_args['chatroom_id'])
                               .one())
        self.chatroom = self.event_chatroom.chatroom
