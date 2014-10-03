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

from flask_pluginengine import render_plugin_template
from wtforms import ValidationError
from wtforms.fields.simple import TextField, TextAreaField

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import PrincipalField, MultipleItemsField
from indico.web.forms.widgets import CKEditorWidget
from MaKaC.webinterface.displayMgr import EventMenuEntry
from MaKaC.webinterface.pages.conferences import WPTPLConferenceDisplay, WPXSLConferenceDisplay

from indico_chat.blueprint import blueprint
from indico_chat.models.chatrooms import ChatroomEventAssociation
from indico_chat.views import WPChatEventPage


class SettingsForm(IndicoForm):
    admins = PrincipalField('Administrators')
    server = TextField('XMPP server')
    muc_server = TextField('XMPP MUC server', description='Usually conference.XMPPSERVER')
    how_to_connect = TextAreaField('How to connect', widget=CKEditorWidget(),
                                   description='Text shown below the chatrooms on an event page')
    chat_links = MultipleItemsField('Chatroom links', fields=(('title', 'Title'), ('link', 'Link')),
                                    description='Links to join the chatroom. You can use the placeholders {room} and '
                                                '{server}.')

    def validate_chat_links(self, field):
        for item in field.data:
            if not all(item.values()):
                raise ValidationError('All fields must contain a value.')


class ChatPlugin(IndicoPlugin):
    """XMPP Chat

    Provides an XMPP based chat for events.
    """

    settings_form = SettingsForm

    @property
    def default_settings(self):
        return {'admins': [],
                'how_to_connect': render_plugin_template('how_to_connect.html'),
                'chat_links': [{'title': 'Desktop Client', 'link': 'xmpp:{room}@{server}?join'}]}

    def init(self):
        super(ChatPlugin, self).init()
        self.connect(signals.event_sidemenu, self.extend_event_menu)
        self.template_hook('event-header', self.inject_event_header)
        for wp in (WPTPLConferenceDisplay, WPXSLConferenceDisplay, WPChatEventPage):
            self.inject_css('chat_css', wp)
            self.inject_js('chat_js', wp)

    def get_blueprints(self):
        return blueprint

    def register_assets(self):
        self.register_css_bundle('chat_css', 'css/chat.scss')
        self.register_js_bundle('chat_js', 'js/chat.js')

    def inject_event_header(self, event, **kwargs):
        chatrooms = ChatroomEventAssociation.find_all(ChatroomEventAssociation.event_id == event.id,
                                                      ~ChatroomEventAssociation.hidden)
        if not chatrooms:
            return ''
        how_to_connect = self.settings.get('how_to_connect')
        return render_plugin_template('event_header.html', event=event, event_chatrooms=chatrooms,
                                      how_to_connect=how_to_connect, chat_links=self.settings.get('chat_links'))

    def _has_visible_chatrooms(self, event):
        return bool(ChatroomEventAssociation.find(ChatroomEventAssociation.event_id == event.id,
                                                  ~ChatroomEventAssociation.hidden).count())

    def extend_event_menu(self, sender, **kwargs):
        return EventMenuEntry('chat.event-page', 'Chat Rooms', name='chat-event-page', plugin=True,
                              visible=self._has_visible_chatrooms)
