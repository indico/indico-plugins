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

from flask_pluginengine import current_plugin
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields.core import BooleanField
from wtforms.fields.simple import StringField, TextAreaField
from wtforms.validators import DataRequired, ValidationError

from indico.web.forms.base import IndicoForm, generated_data
from indico.web.forms.validators import UsedIf

from indico_chat import _
from indico_chat.models.chatrooms import Chatroom
from indico_chat.xmpp import generate_jid, room_exists


class AttachChatroomForm(IndicoForm):
    chatroom = QuerySelectField(_('Available chatrooms'), [DataRequired()], get_label='name')


class EditChatroomForm(IndicoForm):
    event_specific_fields = {'hidden', 'show_password'}

    # Room-wide options
    name = StringField(_('Name'), [DataRequired()], description=_('The name of the room'))
    description = TextAreaField(_('Description'), description=_('The description of the room'))
    password = StringField(_('Password'), description=_('An optional password required to join the room'))
    # Event-specific options
    hidden = BooleanField(_('Hidden'), description=_('Hides the room on public event pages.'))
    show_password = BooleanField(_('Show password'), description=_('Shows the room password on public event pages.'))


class AddChatroomForm(EditChatroomForm):
    use_custom_server = BooleanField(_('Use custom server'))
    custom_server = StringField(_('Custom server'), [UsedIf(lambda form, field: form.use_custom_server.data),
                                                     DataRequired()],
                                filters=[lambda x: x.lower() if x else x],
                                description=_('External Jabber server.'))

    def __init__(self, *args, **kwargs):
        self._date = kwargs.pop('date')
        super(AddChatroomForm, self).__init__(*args, **kwargs)
        self.use_custom_server.description = _('Check in case you want to use an external Jabber server and not the '
                                               'default one ({0}).').format(current_plugin.settings.get('muc_server'))

    def validate_name(self, field):
        jid = generate_jid(field.data, self._date)
        if not jid:
            # This error is not very helpful to a user, but it is extremely unlikely - only if he uses a name
            # which does not contain a single char usable in a JID
            raise ValidationError(_('Could not convert name to a jabber ID'))
        if Chatroom.find_first(jid_node=jid, custom_server=self.custom_server.data):
            raise ValidationError(_('A room with this name already exists'))
        if not self.custom_server.data:
            tmp_room = Chatroom(jid_node=jid)
            if room_exists(tmp_room.jid):
                raise ValidationError(_('A room with this name/JID already exists on the Jabber server ({0})').format(
                    tmp_room.jid
                ))

    @generated_data
    def jid_node(self):
        return generate_jid(self.name.data, self._date)
