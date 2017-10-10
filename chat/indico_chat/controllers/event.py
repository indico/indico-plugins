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
