# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

from indico.core.config import Config
from indico.core.db import db
from indico.modules.users import User
from indico.util.console import cformat
from indico.util.string import is_valid_mail
from indico.util.struct.iterables import committing_iterator

from indico_chat.models.chatrooms import Chatroom, ChatroomEventAssociation
from indico_chat.plugin import ChatPlugin
from indico_zodbimport import Importer, convert_to_unicode, convert_principal_list


class ChatImporter(Importer):
    plugins = {'chat'}

    def pre_check(self):
        return self.check_plugin_schema('chat')

    def has_data(self):
        return Chatroom.find().count()

    def migrate(self):
        # noinspection PyAttributeOutsideInit
        self.chat_root = self.zodb_root['plugins']['InstantMessaging']._PluginType__plugins['XMPP']._storage
        with ChatPlugin.instance.plugin_context():
            self.migrate_settings()
            self.migrate_chatrooms()

    def migrate_settings(self):
        print cformat('%{white!}migrating settings')
        ChatPlugin.settings.delete_all()
        type_opts = self.zodb_root['plugins']['InstantMessaging']._PluginBase__options
        opts = self.zodb_root['plugins']['InstantMessaging']._PluginType__plugins['XMPP']._PluginBase__options
        host = convert_to_unicode(opts['chatServerHost']._PluginOption__value)
        admin_emails = [x.email for x in opts['admins']._PluginOption__value]
        ChatPlugin.settings.set('admins', convert_principal_list(opts['admins']))
        ChatPlugin.settings.set('server', host)
        ChatPlugin.settings.set('muc_server', 'conference.{}'.format(host))
        settings_map = {
            'additionalEmails': 'notify_emails',
            'indicoUsername': 'bot_jid',
            'indicoPassword': 'bot_password',
            'ckEditor': 'how_to_connect'
        }
        for old, new in settings_map.iteritems():
            value = opts[old]._PluginOption__value
            if isinstance(value, basestring):
                value = convert_to_unicode(value).strip()
            elif new == 'notify_emails':
                value = [email for email in set(value + admin_emails) if is_valid_mail(email, multi=False)]
            ChatPlugin.settings.set(new, value)
        if opts['activateLogs']._PluginOption__value:
            ChatPlugin.settings.set('log_url', 'https://{}/logs/'.format(host))
        chat_links = []
        for item in type_opts['customLinks']._PluginOption__value:
            link = item['structure'].replace('[chatroom]', '{room}').replace('[host]', '{server}')
            link = re.sub(r'(?<!conference\.)\{server}', host, link)
            link = link.replace('conference.{server}', '{server}')  # {server} is now the MUC server
            chat_links.append({'title': item['name'], 'link': link})
        ChatPlugin.settings.set('chat_links', chat_links)
        db.session.commit()

    def migrate_chatrooms(self):
        print cformat('%{white!}migrating chatrooms')
        default_server = ChatPlugin.settings.get('muc_server')
        chatrooms = {}
        for old_room in committing_iterator(self.chat_root['indexByID']._data.itervalues()):
            has_custom_server = not old_room._createdInLocalServer and old_room._host != default_server
            custom_server = convert_to_unicode(old_room._host) if has_custom_server else ''
            identifier = (custom_server, old_room._name.lower())
            room = chatrooms.get(identifier)
            if room:
                print cformat('- %{cyan}{}   %{yellow!}DUPLICATE%{reset}').format(room.name)
            else:
                user = User.get(int(old_room._owner.id)) or User.get(Config.getInstance().getJanitorUserId())
                room = Chatroom(jid_node=convert_to_unicode(old_room._name.lower()),
                                name=convert_to_unicode(old_room._name),
                                description=convert_to_unicode(old_room._description),
                                password=convert_to_unicode(old_room._password),
                                custom_server=custom_server,
                                created_by_user=user,
                                created_dt=old_room._creationDate,
                                modified_dt=old_room._modificationDate)
                chatrooms[identifier] = room
                db.session.add(room)
                print cformat('- %{cyan}{}').format(room.name)
                if room.custom_server:
                    print cformat('  %{blue!}Custom server:%{reset} {}').format(room.custom_server)

            events = set()
            for event in old_room._conferences:
                assoc = ChatroomEventAssociation(event_id=int(event),
                                                 chatroom=room,
                                                 hidden=not old_room._showRoom,
                                                 show_password=old_room._showPass)
                db.session.add(assoc)
                events.add(assoc.event_id)
            if events:
                print cformat('  %{blue!}Events:%{reset} {}').format(', '.join(map(unicode, events)))
            else:
                print cformat('  %{yellow!}no events%{reset}')
