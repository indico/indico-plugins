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

import re

from flask import current_app
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError

from indico.core.logger import Logger
from indico.util.string import unicode_to_ascii
from indico_chat.util import check_config


INVALID_JID_CHARS = re.compile(r'[^-!#()*+,.=^_a-z0-9]')
WHITESPACE = re.compile(r'\s+')


def create_room(room):
    """Creates a MUC room on the XMPP server."""

    def _create_room(xmpp):
        muc = xmpp.plugin['xep_0045']
        muc.joinMUC(room.jid, xmpp.requested_jid.user)
        muc.configureRoom(room.jid, _set_form_values(xmpp, room))

    Logger.get('plugin.chat').info('Creating room {}'.format(room.jid))
    return _execute_xmpp(_create_room)


def update_room(room):
    """Updates a MUC room on the XMPP server."""

    def _update_room(xmpp):
        muc = xmpp.plugin['xep_0045']
        muc.joinMUC(room.jid, xmpp.requested_jid.user)
        muc.configureRoom(room.jid, _set_form_values(xmpp, room, muc.getRoomConfig(room.jid)))

    Logger.get('plugin.chat').info('Updating room {}'.format(room.jid))
    return _execute_xmpp(_update_room)


def delete_room(jid, reason=''):
    """Deletes a MUC room from the XMPP server."""

    def _delete_room(xmpp):
        muc = xmpp.plugin['xep_0045']
        muc.destroy(jid, reason=reason)

    Logger.get('plugin.chat').info('Deleting room {}'.format(jid))
    return _execute_xmpp(_delete_room)


def get_room_config(jid):
    """Retrieves basic data of a MUC room from the XMPP server.

    :return: dict containing name, description and password of the room
    """

    mapping = {
        'name': 'muc#roomconfig_roomname',
        'description': 'muc#roomconfig_roomdesc',
        'password': 'muc#roomconfig_roomsecret'
    }

    def _get_room_config(xmpp):
        muc = xmpp.plugin['xep_0045']
        try:
            form = muc.getRoomConfig(jid)
        except ValueError:  # probably the room doesn't exist
            return None
        fields = form.values['fields']
        return {key: fields[muc_key].values['value'] for key, muc_key in mapping.iteritems()}

    return _execute_xmpp(_get_room_config)


def room_exists(jid):
    """Checks if a MUC room exists on the server."""

    def _room_exists(xmpp):
        disco = xmpp.plugin['xep_0030']
        try:
            disco.get_info(jid)
        except IqError as e:
            if e.condition == 'item-not-found':
                return False
            raise
        else:
            return True

    return _execute_xmpp(_room_exists)


def sanitize_jid(s):
    """Generates a valid JID node identifier from a string"""
    jid = unicode_to_ascii(s).lower()
    jid = WHITESPACE.sub('-', jid)
    jid = INVALID_JID_CHARS.sub('', jid)
    return jid.strip()[:256]


def generate_jid(name, append_date=None):
    """Generates a v alid JID based on the room name.

    :param append_date: appends the given date to the JID
    """
    if not append_date:
        return sanitize_jid(name)
    return '{}-{}'.format(sanitize_jid(name), append_date.strftime('%Y-%m-%d'))


def _set_form_values(xmpp, room, form=None):
    """Creates/Updates an XMPP room config form"""
    if form is None:
        form = xmpp.plugin['xep_0004'].make_form(ftype='submit')
        form.add_field('FORM_TYPE', value='http://jabber.org/protocol/muc#roomconfig')
        form.add_field('muc#roomconfig_publicroom', value='1')
        form.add_field('muc#roomconfig_whois', value='moderators')
        form.add_field('muc#roomconfig_membersonly', value='0')
        form.add_field('muc#roomconfig_moderatedroom', value='1')
        form.add_field('muc#roomconfig_changesubject', value='1')
        form.add_field('muc#roomconfig_allowinvites', value='1')
        form.add_field('muc#roomconfig_allowvisitorstatus', value='1')
        form.add_field('muc#roomconfig_allowvisitornickchange', value='1')
        form.add_field('muc#roomconfig_enablelogging', value='1')
        form.add_field('public_list', value='1')
        form.add_field('members_by_default', value='1')
        form.add_field('allow_private_messages', value='1')
        form.add_field('allow_query_users', value='1')
    form.add_field('muc#roomconfig_persistentroom', value='1')
    form.add_field('muc#roomconfig_roomname', value=room.name)
    form.add_field('muc#roomconfig_passwordprotectedroom', value='1' if room.password else '0')
    if room.description:
        form.add_field('muc#roomconfig_roomdesc', value=room.description)
    if room.password:
        form.add_field('muc#roomconfig_roomsecret', value=room.password)
    return form


def _execute_xmpp(connected_callback):
    """Connects to the XMPP server and executes custom code

    :param connected_callback: function to execute after connecting
    :return: return value of the callback
    """
    from indico_chat.plugin import ChatPlugin

    check_config()
    jid = ChatPlugin.settings.get('bot_jid')
    password = ChatPlugin.settings.get('bot_password')
    if '@' not in jid:
        jid = '{}@{}'.format(jid, ChatPlugin.settings.get('server'))

    result = [None, None]  # result, exception
    app = current_app._get_current_object()  # callback runs in another thread

    def _session_start(event):
        try:
            with app.app_context():
                result[0] = connected_callback(xmpp)
        except Exception as e:
            result[1] = e
            if isinstance(e, IqError):
                Logger.get('plugin.chat').exception('XMPP callback failed: {}'.format(e.condition))
            else:
                Logger.get('plugin.chat').exception('XMPP callback failed')
        finally:
            xmpp.disconnect(wait=0)

    xmpp = ClientXMPP(jid, password)
    xmpp.register_plugin('xep_0045')
    xmpp.register_plugin('xep_0004')
    xmpp.register_plugin('xep_0030')
    xmpp.add_event_handler('session_start', _session_start)

    try:
        xmpp.connect()
    except Exception:
        Logger.get('plugin.chat').exception('XMPP connection failed')
        xmpp.disconnect()
        raise

    try:
        xmpp.process(threaded=False)
    finally:
        xmpp.disconnect(wait=0)

    if result[1] is not None:
        raise result[1]

    return result[0]
