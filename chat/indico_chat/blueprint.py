# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
