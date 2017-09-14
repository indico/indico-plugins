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

from indico.core.plugins import IndicoPluginBlueprint

from indico_chat.controllers.event import RHChatEventPage
from indico_chat.controllers.logs import RHChatManageEventAttachLogs, RHChatManageEventLogs, RHChatManageEventShowLogs
from indico_chat.controllers.management import (RHChatManageEvent, RHChatManageEventAttach, RHChatManageEventCreate,
                                                RHChatManageEventModify, RHChatManageEventRefresh,
                                                RHChatManageEventRemove)


blueprint = IndicoPluginBlueprint('chat', 'indico_chat', url_prefix='/event/<confId>')

# Event
blueprint.add_url_rule('/chat', 'event_page', RHChatEventPage)

# Event management
blueprint.add_url_rule('/manage/chat/', 'manage_rooms', RHChatManageEvent)
blueprint.add_url_rule('/manage/chat/<int:chatroom_id>/', 'manage_rooms_modify', RHChatManageEventModify,
                       methods=('GET', 'POST'))
blueprint.add_url_rule('/manage/chat/<int:chatroom_id>/logs/', 'manage_rooms_logs', RHChatManageEventLogs)
blueprint.add_url_rule('/manage/chat/<int:chatroom_id>/logs/show', 'manage_rooms_show_logs',
                       RHChatManageEventShowLogs)
blueprint.add_url_rule('/manage/chat/<int:chatroom_id>/logs/attach', 'manage_rooms_attach_logs',
                       RHChatManageEventAttachLogs, methods=('POST',))
blueprint.add_url_rule('/manage/chat/<int:chatroom_id>/refresh', 'manage_rooms_refresh', RHChatManageEventRefresh,
                       methods=('POST',))
blueprint.add_url_rule('/manage/chat/<int:chatroom_id>/remove', 'manage_rooms_remove', RHChatManageEventRemove,
                       methods=('POST',))
blueprint.add_url_rule('/manage/chat/create', 'manage_rooms_create', RHChatManageEventCreate,
                       methods=('GET', 'POST'))
blueprint.add_url_rule('/manage/chat/attach', 'manage_rooms_attach', RHChatManageEventAttach, methods=('POST',))
