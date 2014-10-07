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

from wtforms.fields.core import BooleanField
from wtforms.fields.simple import TextField, TextAreaField
from wtforms.validators import DataRequired, ValidationError

from indico.web.forms.base import IndicoForm
from indico.util.string import strip_whitespace

from indico_chat.models.chatrooms import Chatroom
from indico_chat.xmpp import generate_jid


class EditChatroomForm(IndicoForm):
    event_specific_fields = {'hidden', 'show_password'}

    # Room-wide options
    name = TextField('Name', [DataRequired()], filters=[strip_whitespace], description='The name of the room')
    description = TextAreaField('Description', filters=[strip_whitespace], description='The description of the room')
    password = TextField('Password', filters=[strip_whitespace],
                         description='An optional password required to join the room')
    # Event-specific options
    hidden = BooleanField('Hidden', description='Hides the room on public event pages.')
    show_password = BooleanField('Show password', description='Shows the room password on public event pages.')


class AddChatroomForm(EditChatroomForm):
    custom_server = TextField('Server', filters=[strip_whitespace, lambda x: x.lower() if x else x],
                              description='External Jabber server. Should be left empty in most cases.')

    def validate_name(self, field):
        jid = generate_jid(field.data)
        if not jid:
            # This error is not very helpful to a user, but it is extremely unlikely - only if he uses a name
            # which does not contain a single char usable in a JID
            raise ValidationError('Could not convert name to a jabber ID')
        if Chatroom.find_first(jid_node=jid, custom_server=self.custom_server.data):
            raise ValidationError('A room with this name already exists')
