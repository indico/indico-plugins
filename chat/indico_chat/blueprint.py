# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from indico.core.plugins import IndicoPluginBlueprint

from indico_chat.controllers import (RHChatEventPage, RHChatManageEvent, RHChatManageEventModify,
                                     RHChatManageEventRefresh, RHChatManageEventRemove, RHChatManageEventCreate,
                                     RHChatManageEventAttach)

# TODO: s/chat-new/chat/
blueprint = IndicoPluginBlueprint('chat', 'indico_chat', url_prefix='/event/<confId>')
blueprint.add_url_rule('/chat-new', 'event_page', RHChatEventPage)
blueprint.add_url_rule('/manage/chat-new/', 'manage_rooms', RHChatManageEvent)
blueprint.add_url_rule('/manage/chat-new/<int:chatroom_id>/', 'manage_rooms_modify', RHChatManageEventModify,
                       methods=('GET', 'POST'))
blueprint.add_url_rule('/manage/chat-new/<int:chatroom_id>/refresh', 'manage_rooms_refresh', RHChatManageEventRefresh,
                       methods=('POST',))
blueprint.add_url_rule('/manage/chat-new/<int:chatroom_id>/remove', 'manage_rooms_remove', RHChatManageEventRemove,
                       methods=('POST',))
blueprint.add_url_rule('/manage/chat-new/create', 'manage_rooms_create', RHChatManageEventCreate,
                       methods=('GET', 'POST'))
blueprint.add_url_rule('/manage/chat-new/attach', 'manage_rooms_attach', RHChatManageEventAttach, methods=('POST',))
