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

from indico.core.config import Config
from indico.core.plugins import get_plugin_template_module
from MaKaC.common.mail import GenericMailer
from MaKaC.webinterface.mail import GenericNotification

from indico_chat.util import get_chat_admins


def notify_created(room, event, user):
    """Notifies about the creation of a chatroom.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action
    """
    tpl = get_plugin_template_module('emails/created.txt', chatroom=room, event=event, user=user)
    _send(event, tpl.get_subject(), tpl.get_body())


def notify_attached(room, event, user):
    """Notifies about an existing chatroom being attached to an event.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action
    """
    tpl = get_plugin_template_module('emails/attached.txt', chatroom=room, event=event, user=user)
    _send(event, tpl.get_subject(), tpl.get_body())


def notify_modified(room, event, user):
    """Notifies about the modification of a chatroom.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action
    """
    tpl = get_plugin_template_module('emails/modified.txt', chatroom=room, event=event, user=user)
    _send(event, tpl.get_subject(), tpl.get_body())


def notify_deleted(room, event, user, room_deleted):
    """Notifies about the deletion of a chatroom.

    :param room: the chatroom
    :param event: the event
    :param user: the user performing the action; `None` if due to event deletion
    :param room_deleted: if the room has been deleted from the jabber server
    """
    tpl = get_plugin_template_module('emails/deleted.txt', chatroom=room, event=event, user=user,
                                     room_deleted=room_deleted)
    _send(event, tpl.get_subject(), tpl.get_body())


def _send(event, subject, body):
    from indico_chat.plugin import ChatPlugin

    to_list = set(ChatPlugin.settings.get('notify_emails'))
    if ChatPlugin.settings.get('notify_admins'):
        to_list |= {u.getEmail() for u in get_chat_admins()}
    if not to_list:
        return
    notification = {
        'fromAddr': Config.getInstance().getNoReplyEmail(),
        'toList': to_list,
        'subject': subject,
        'body': body
    }
    GenericMailer.sendAndLog(GenericNotification(notification), event, 'chat')
