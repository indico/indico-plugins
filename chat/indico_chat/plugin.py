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

from flask import session
from flask_pluginengine import render_plugin_template
from wtforms import ValidationError
from wtforms.fields.core import BooleanField
from wtforms.fields.html5 import URLField
from wtforms.fields.simple import TextField, TextAreaField
from wtforms.validators import DataRequired

from indico.core import signals
from indico.core.db import db
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.util.i18n import _
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import PrincipalField, MultipleItemsField, EmailListField, UnsafePasswordField
from indico.web.forms.widgets import CKEditorWidget
from MaKaC.accessControl import AccessWrapper
from MaKaC.conference import EventCloner
from MaKaC.webinterface.displayMgr import EventMenuEntry
from MaKaC.webinterface.pages.conferences import WPTPLConferenceDisplay, WPXSLConferenceDisplay
from MaKaC.webinterface.wcomponents import SideMenuItem

from indico_chat.blueprint import blueprint
from indico_chat.models.chatrooms import ChatroomEventAssociation
from indico_chat.notifications import notify_deleted
from indico_chat.util import is_chat_admin
from indico_chat.views import WPChatEventPage, WPChatEventMgmt


class SettingsForm(IndicoForm):
    admins = PrincipalField(_('Administrators'), description=_('Users who can manage chatrooms for all events'))
    server = TextField(_('XMPP server'), [DataRequired()], description=_('The hostname of the XMPP server'))
    muc_server = TextField(_('XMPP MUC server'), [DataRequired()], description=_("The hostname of the XMPP MUC server"))
    bot_jid = TextField(_('Bot JID'), [DataRequired()],
                        description=_("Jabber ID of the XMPP bot. Can be just a username (in that case the default "
                                      "server is assumed) or a username@server."))
    bot_password = UnsafePasswordField(_('Bot Password'), [DataRequired()], description=_("Password for the bot"))
    notify_admins = BooleanField(_('Notify admins'),
                                 description=_("Should chat administrators receive email notifications?"))
    notify_emails = EmailListField(_('Notification emails'),
                                   description=_("Additional email addresses to sent notifications to (one per line)"))
    log_url = URLField(_('Log URL'), description=_('You can set this to the URL of the '
                                                   '<a href="https://github.com/indico/jabber-logs/">jabber-logs '
                                                   'app</a>, running on the jabber server to let event managers can '
                                                   'retrieve chat logs for rooms on that server.'))
    chat_links = MultipleItemsField(_('Chatroom links'), fields=(('title', 'Title'), ('link', 'Link')),
                                    description=_("Links to join the chatroom. You can use the placeholders {room} for "
                                                  "the room name and {server} for the MUC server."))
    how_to_connect = TextAreaField(_('How to connect'), widget=CKEditorWidget(),
                                   description=_("Text shown below the chatrooms on an event page"))

    def validate_chat_links(self, field):
        for item in field.data:
            if not all(item.values()):
                raise ValidationError(_('All fields must contain a value.'))


class ChatPlugin(IndicoPlugin):
    """XMPP Chat

    Provides an XMPP based chat for events.
    """

    settings_form = SettingsForm
    settings_form_field_opts = {
        'server': {'placeholder': 'jabber.server.tld'},
        'muc_server': {'placeholder': 'conference.jabber.server.tld'},
        'notify_emails': {'rows': 3, 'cols': 40, 'style': 'width: auto; height: auto;'},
        'bot_jid': {'autocomplete': 'off'},
        'bot_password': {'autocomplete': 'off'}
    }

    @property
    def default_settings(self):
        return {'admins': [],
                'notify_admins': False,
                'notify_emails': [],
                'how_to_connect': render_plugin_template('how_to_connect.html'),
                'chat_links': [{'title': 'Desktop Client', 'link': 'xmpp:{room}@{server}?join'}]}

    def init(self):
        super(ChatPlugin, self).init()
        self.connect(signals.event_sidemenu, self.extend_event_menu)
        self.connect(signals.event_management_sidemenu, self.extend_event_management_menu)
        self.connect(signals.event_management_clone, self.extend_event_management_clone)
        self.connect(signals.event_deleted, self.event_deleted)
        self.connect(signals.event_management_url, self.get_event_management_url)
        self.template_hook('event-header', self.inject_event_header)
        for wp in (WPTPLConferenceDisplay, WPXSLConferenceDisplay, WPChatEventPage, WPChatEventMgmt):
            self.inject_css('chat_css', wp)
            self.inject_js('chat_js', wp)

    def get_blueprints(self):
        return blueprint

    def register_assets(self):
        self.register_css_bundle('chat_css', 'css/chat.scss')
        self.register_js_bundle('chat_js', 'js/chat.js')

    def inject_event_header(self, event, **kwargs):
        chatrooms = ChatroomEventAssociation.find_for_event(event).all()
        if not chatrooms:
            return ''
        how_to_connect = self.settings.get('how_to_connect')
        return render_plugin_template('event_header.html', event=event, event_chatrooms=chatrooms,
                                      how_to_connect=how_to_connect, chat_links=self.settings.get('chat_links'))

    def _has_visible_chatrooms(self, event):
        return bool(ChatroomEventAssociation.find_for_event(event).count())

    def extend_event_menu(self, sender, **kwargs):
        return EventMenuEntry('chat.event_page', 'Chat Rooms', name='chat-event-page', plugin=True,
                              visible=self._has_visible_chatrooms)

    def extend_event_management_menu(self, event, **kwargs):
        if event.canModify(AccessWrapper(session.user)) or is_chat_admin(session.user):
            return 'chat-management', SideMenuItem('Chat Rooms', url_for_plugin('chat.manage_rooms', event))

    def extend_event_management_clone(self, event, **kwargs):
        return ChatroomCloner(self, event)

    def get_event_management_url(self, event, **kwargs):
        if is_chat_admin(session.user):
            return url_for_plugin('chat.manage_rooms', event)

    def event_deleted(self, event, **kwargs):
        for event_chatroom in ChatroomEventAssociation.find_for_event(event, include_hidden=True):
            chatroom_deleted = event_chatroom.delete()
            notify_deleted(event_chatroom.chatroom, event, None, chatroom_deleted)


class ChatroomCloner(EventCloner):
    def get_options(self):
        enabled = bool(ChatroomEventAssociation.find_for_event(self.event, include_hidden=True).count())
        return {'chatrooms': (_('Chatrooms'), enabled)}

    def clone(self, new_event, options):
        """Called when the event is being cloned"""
        if 'chatrooms' not in options:
            return
        for old_event_chatroom in ChatroomEventAssociation.find_for_event(self.event, include_hidden=True):
            event_chatroom = ChatroomEventAssociation(chatroom=old_event_chatroom.chatroom,
                                                      event_id=int(new_event.id),
                                                      hidden=old_event_chatroom.hidden,
                                                      show_password=old_event_chatroom.show_password)
            db.session.add(event_chatroom)
