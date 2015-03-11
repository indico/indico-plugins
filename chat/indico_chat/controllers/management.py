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

from flask import session, request, flash, redirect, jsonify
from flask_pluginengine import current_plugin

from indico.core.db import db
from indico.core.db.sqlalchemy.util.models import attrs_changed
from indico.core.errors import IndicoError
from indico.core.plugins import url_for_plugin
from indico.util.date_time import now_utc
from indico.util.string import to_unicode
from indico.web.forms.base import FormDefaults

from indico_chat import _
from indico_chat.controllers.base import RHChatManageEventBase, RHEventChatroomMixin
from indico_chat.forms import AddChatroomForm, EditChatroomForm
from indico_chat.models.chatrooms import ChatroomEventAssociation, Chatroom
from indico_chat.notifications import notify_created, notify_attached, notify_modified, notify_deleted
from indico_chat.views import WPChatEventMgmt
from indico_chat.xmpp import create_room, update_room, get_room_config, room_exists


class RHChatManageEvent(RHChatManageEventBase):
    """Lists the chatrooms of an event"""

    def _process(self):
        chatrooms = ChatroomEventAssociation.find_for_event(self.event, include_hidden=True,
                                                            _eager='chatroom.events').all()
        chatroom_filter = (~Chatroom.id.in_(x.chatroom_id for x in chatrooms)) if chatrooms else True
        available_chatrooms = Chatroom.find_all(Chatroom.created_by_id == int(session.user.id), chatroom_filter)
        logs_enabled = current_plugin.settings.get('log_url')
        return WPChatEventMgmt.render_template('manage_event.html', self._conf, event_chatrooms=chatrooms,
                                               event=self.event, chat_links=current_plugin.settings.get('chat_links'),
                                               available_chatrooms=available_chatrooms, logs_enabled=logs_enabled)


class RHChatManageEventModify(RHEventChatroomMixin, RHChatManageEventBase):
    """Modifies an existing chatroom"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

    def _process(self):
        defaults = FormDefaults(self.chatroom)
        for name in EditChatroomForm.event_specific_fields:
            defaults[name] = getattr(self.event_chatroom, name)
        form = EditChatroomForm(obj=defaults)
        if form.validate_on_submit():
            form.populate_obj(self.event_chatroom, fields=form.event_specific_fields)
            form.populate_obj(self.chatroom, skip=form.event_specific_fields)
            self.chatroom.modified_dt = now_utc()
            if attrs_changed(self.chatroom, 'name', 'description', 'password'):
                update_room(self.chatroom)
            notify_modified(self.chatroom, self.event, session.user)
            flash(_('Chatroom updated'), 'success')
            return redirect(url_for_plugin('.manage_rooms', self.event))
        return WPChatEventMgmt.render_template('manage_event_edit.html', self._conf, form=form,
                                               event_chatroom=self.event_chatroom, event=self.event)


class RHChatManageEventRefresh(RHEventChatroomMixin, RHChatManageEventBase):
    """Synchronizes the local chatroom data with the XMPP server"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

    def _process(self):
        if self.chatroom.custom_server:
            return jsonify(result='')

        config = get_room_config(self.chatroom.jid)
        if config is None:
            if not room_exists(self.chatroom.jid):
                return jsonify(result='not-found')
            raise IndicoError(_('Unexpected result from Jabber server'))

        changed = False
        for key, value in config.iteritems():
            if getattr(self.chatroom, key) != value:
                changed = True
                setattr(self.chatroom, key, value)

        return jsonify(result='changed' if changed else '')


class RHChatManageEventCreate(RHChatManageEventBase):
    """Creates a new chatroom for an event"""

    def _process(self):
        form = AddChatroomForm(obj=FormDefaults(name=to_unicode(self.event.title)),
                               date=self.event.getAdjustedStartDate())
        if form.validate_on_submit():
            chatroom = Chatroom(created_by_user=session.user)
            event_chatroom = ChatroomEventAssociation(event_id=self.event_id, chatroom=chatroom)
            form.populate_obj(event_chatroom, fields=form.event_specific_fields)
            form.populate_obj(chatroom, skip=form.event_specific_fields)
            chatroom.jid_node = form.jid_node.data
            db.session.add_all((chatroom, event_chatroom))
            db.session.flush()
            create_room(chatroom)
            notify_created(chatroom, self.event, session.user)
            flash(_('Chatroom created'), 'success')
            return redirect(url_for_plugin('.manage_rooms', self.event))
        return WPChatEventMgmt.render_template('manage_event_edit.html', self._conf, form=form, event=self.event)


class RHChatManageEventAttach(RHChatManageEventBase):
    """Attaches an existing chatroom to an event"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        self.chatroom = Chatroom.find_one(id=request.form['chatroom_id'])

    def _process(self):
        event_chatroom = ChatroomEventAssociation(event_id=self.event_id, chatroom=self.chatroom)
        db.session.add(event_chatroom)
        notify_attached(self.chatroom, self.event, session.user)
        flash(_('Chatroom added'), 'success')
        return redirect(url_for_plugin('.manage_rooms', self.event))


class RHChatManageEventRemove(RHEventChatroomMixin, RHChatManageEventBase):
    """Removes a chatroom from an event (and if necessary from the server)"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

    def _process(self):
        reason = '{} has requested to delete this room.'.format(to_unicode(session.user.getStraightFullName()))
        chatroom_deleted = self.event_chatroom.delete(reason)
        notify_deleted(self.chatroom, self.event, session.user, chatroom_deleted)
        if chatroom_deleted:
            flash(_('Chatroom deleted'), 'success')
        else:
            flash(_('Chatroom removed from event'), 'success')
        return redirect(url_for_plugin('.manage_rooms', self.event))
