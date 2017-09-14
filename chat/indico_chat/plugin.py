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

from flask import session
from flask_pluginengine import render_plugin_template
from wtforms import ValidationError
from wtforms.fields.html5 import URLField
from wtforms.fields.simple import StringField, TextAreaField
from wtforms.validators import DataRequired

from indico.core import signals
from indico.core.db import db
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.cloning import EventCloner
from indico.modules.events.layout.util import MenuEntryData
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import EmailListField, IndicoPasswordField, MultipleItemsField, PrincipalListField
from indico.web.forms.widgets import CKEditorWidget
from indico.web.menu import SideMenuItem

from indico_chat import _
from indico_chat.blueprint import blueprint
from indico_chat.models.chatrooms import ChatroomEventAssociation
from indico_chat.notifications import notify_deleted
from indico_chat.util import is_chat_admin
from indico_chat.views import WPChatEventMgmt


class SettingsForm(IndicoForm):
    admins = PrincipalListField(_('Administrators'), groups=True,
                                description=_('List of users/groups who can manage chatrooms for all events'))
    server = StringField(_('XMPP server'), [DataRequired()], description=_('The hostname of the XMPP server'))
    muc_server = StringField(_('XMPP MUC server'), [DataRequired()],
                             description=_("The hostname of the XMPP MUC server"))
    bot_jid = StringField(_('Bot JID'), [DataRequired()],
                          description=_("Jabber ID of the XMPP bot. Can be just a username (in that case the default "
                                        "server is assumed) or a username@server."))
    bot_password = IndicoPasswordField(_('Bot Password'), [DataRequired()], toggle=True,
                                       description=_("Password for the bot"))
    notify_emails = EmailListField(_('Notification emails'),
                                   description=_("Email addresses to sent notifications to (one per line)"))
    log_url = URLField(_('Log URL'), description=_('You can set this to the URL of the '
                                                   '<a href="https://github.com/indico/jabber-logs/">jabber-logs '
                                                   'app</a>, running on the jabber server to let event managers can '
                                                   'retrieve chat logs for rooms on that server.'))
    chat_links = MultipleItemsField(_('Chatroom links'),
                                    fields=[{'id': 'title', 'caption': _("Title"), 'required': True},
                                            {'id': 'link', 'caption': _("Link"), 'required': True}],
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
    configurable = True
    settings_form = SettingsForm
    settings_form_field_opts = {
        'server': {'placeholder': 'jabber.server.tld'},
        'muc_server': {'placeholder': 'conference.jabber.server.tld'},
        'notify_emails': {'rows': 3, 'cols': 40, 'style': 'height: auto;'},
        'bot_jid': {'autocomplete': 'off'},
        'bot_password': {'autocomplete': 'off'}
    }
    acl_settings = {'admins'}

    @property
    def default_settings(self):
        return {
            'server': '',
            'muc_server': '',
            'bot_jid': '',
            'bot_password': '',
            'notify_emails': [],
            'log_url': '',
            'chat_links': [{'title': 'Desktop Client', 'link': 'xmpp:{room}@{server}?join'}],
            'how_to_connect': render_plugin_template('how_to_connect.html')
        }

    def init(self):
        super(ChatPlugin, self).init()
        self.connect(signals.event.sidemenu, self.extend_event_menu)
        self.connect(signals.event.deleted, self.event_deleted)
        self.connect(signals.menu.items, self.extend_event_management_menu, sender='event-management-sidemenu')
        self.connect(signals.event_management.get_cloners, self._get_event_cloners)
        self.connect(signals.event_management.management_url, self.get_event_management_url)
        self.connect(signals.users.merged, self._merge_users)
        self.template_hook('event-header', self.inject_event_header)
        self.inject_css('chat_css', WPChatEventMgmt)
        self.inject_js('chat_js', WPChatEventMgmt)

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

    def extend_event_menu(self, sender, **kwargs):
        return MenuEntryData(_('Chat Rooms'), 'chatrooms', 'chat.event_page', position=-1,
                             visible=lambda event: ChatroomEventAssociation.find_for_event(event).has_rows())

    def extend_event_management_menu(self, sender, event, **kwargs):
        if event.can_manage(session.user) or is_chat_admin(session.user):
            return SideMenuItem('chat', 'Chat Rooms', url_for_plugin('chat.manage_rooms', event), section='services')

    def _get_event_cloners(self, sender, **kwargs):
        return ChatroomCloner

    def get_event_management_url(self, event, **kwargs):
        if is_chat_admin(session.user):
            return url_for_plugin('chat.manage_rooms', event)

    def event_deleted(self, event, **kwargs):
        for event_chatroom in ChatroomEventAssociation.find_for_event(event, include_hidden=True):
            chatroom_deleted = event_chatroom.delete()
            notify_deleted(event_chatroom.chatroom, event, None, chatroom_deleted)

    def _merge_users(self, target, source, **kwargs):
        self.settings.acls.merge_users(target, source)


class ChatroomCloner(EventCloner):
    name = 'chatrooms'
    friendly_name = _('Chatrooms')

    @property
    def is_available(self):
        return bool(self.old_event.chatroom_associations.count())

    def run(self, new_event, cloners, shared_data):
        for old_event_chatroom in self.old_event.chatroom_associations:
            event_chatroom = ChatroomEventAssociation(chatroom=old_event_chatroom.chatroom,
                                                      hidden=old_event_chatroom.hidden,
                                                      show_password=old_event_chatroom.show_password)
            new_event.chatroom_associations.append(event_chatroom)
        db.session.flush()
