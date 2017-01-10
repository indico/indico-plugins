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

from indico.core.notifications import make_email, send_email
from indico.core.plugins import get_plugin_template_module


def notify_created(room, event, user):
    """Notifies about the creation of a chatroom.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action
    """
    tpl = get_plugin_template_module('emails/created.txt', chatroom=room, event=event, user=user)
    _send(event, tpl)


def notify_attached(room, event, user):
    """Notifies about an existing chatroom being attached to an event.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action
    """
    tpl = get_plugin_template_module('emails/attached.txt', chatroom=room, event=event, user=user)
    _send(event, tpl)


def notify_modified(room, event, user):
    """Notifies about the modification of a chatroom.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action
    """
    tpl = get_plugin_template_module('emails/modified.txt', chatroom=room, event=event, user=user)
    _send(event, tpl)


def notify_deleted(room, event, user, room_deleted):
    """Notifies about the deletion of a chatroom.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action; `None` if due to event deletion
    :param room_deleted: if the room has been deleted from the jabber server
    """
    tpl = get_plugin_template_module('emails/deleted.txt', chatroom=room, event=event, user=user,
                                     room_deleted=room_deleted)
    _send(event, tpl)


def _send(event, template_module):
    from indico_chat.plugin import ChatPlugin

    to_list = set(ChatPlugin.settings.get('notify_emails'))
    if not to_list:
        return

    send_email(make_email(to_list, template=template_module), event, 'Chat')
