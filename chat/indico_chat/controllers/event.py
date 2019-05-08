# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask_pluginengine import current_plugin

from indico.modules.events.controllers.base import RHDisplayEventBase

from indico_chat.models.chatrooms import ChatroomEventAssociation
from indico_chat.views import WPChatEventPage


class RHChatEventPage(RHDisplayEventBase):
    """Lists the public chatrooms in a conference"""

    def _process(self):
        chatrooms = ChatroomEventAssociation.find_for_event(self.event).all()
        cols = set()
        if any(c.chatroom.description for c in chatrooms):
            cols.add('description')
        if any(c.chatroom.password for c in chatrooms):
            cols.add('password')
        return WPChatEventPage.render_template('event_page.html', self.event, event_chatrooms=chatrooms, cols=cols,
                                               chat_links=current_plugin.settings.get('chat_links'))
