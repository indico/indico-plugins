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

import re

from wtforms.fields.core import BooleanField, SelectField
from wtforms.fields.simple import StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Regexp, Optional, ValidationError

from indico.modules.vc.models import VCRoom
from indico.modules.vc.plugins import VCRoomFormBase
from indico.util.i18n import _
from indico.util.user import retrieve_principal
from indico.web.forms.fields import PrincipalField, IndicoPasswordField, IndicoRadioField
from indico.web.forms.widgets import SwitchWidget, JinjaWidget


ROOM_NAME_RE = re.compile(r'[\w\-]+')
PIN_RE = re.compile(r'^\d+$')

ERROR_MSG_PIN = _("The PIN must be a number")


class VCRoomForm(VCRoomFormBase):
    """Contains all information concerning a Vidyo booking"""

    advanced_fields = {'show_pin', 'show_autojoin', 'show_phone_numbers', 'show'}
    conditional_fields = {'contribution', 'session'}
    skip_fields = advanced_fields | conditional_fields

    name = StringField(_('Name'), [DataRequired(), Length(min=3, max=60), Regexp(ROOM_NAME_RE)],
                       description=_('The name of the room'))
    description = TextAreaField(_('Description'), [DataRequired()], description=_('The description of the room'))

    linking = IndicoRadioField(_("Link to"), [DataRequired()],
                               choices=[('event', _("Event")),
                                        ('contribution', _("Contribution")),
                                        ('session', _("Session"))],
                               widget=JinjaWidget('linking_widget.html', plugin='vc_vidyo'))
    contribution = SelectField(_("Contribution"), [DataRequired()])
    session = SelectField(_("Session"), [DataRequired()])
    moderator = PrincipalField(_('Moderator'), [DataRequired()], multiple=False,
                               description=_('The moderator of the room'))
    moderator_pin = IndicoPasswordField(
        _('Moderator PIN'),
        [Optional(), Length(min=3, max=10), Regexp(PIN_RE)],
        toggle=True, description=_('Used to moderate the VC Room'))
    room_pin = IndicoPasswordField(
        _('Room PIN'),
        [Optional(), Length(min=3, max=10), Regexp(PIN_RE, message=ERROR_MSG_PIN)],
        toggle=True, description=_('Used to protect the access to the VC Room (leave blank for open access)'))
    auto_mute = BooleanField(_('Auto mute'),
                             widget=SwitchWidget(_('On'), _('Off')),
                             description=_('The VidyoDesktop clients will join the VC room muted by default '
                                           '(audio and video)'))

    # Advanced options
    show_pin = BooleanField(_('Show PIN'),
                            widget=SwitchWidget(),
                            description=_("Show the VC Room PIN on the event page (insecure!)"))
    show_autojoin = BooleanField(_('Show Auto-join URL'),
                                 widget=SwitchWidget(),
                                 description=_("Show the auto-join URL on the event page"))
    show_phone_numbers = BooleanField(_('Show Phone Access numbers'),
                                      widget=SwitchWidget(),
                                      description=_("Show a link to the list of phone access numbers"))
    show = BooleanField(_('Show room'),
                        widget=SwitchWidget(),
                        description=_('Display this room on the event page'))

    def __init__(self, *args, **kwargs):
        super(VCRoomForm, self).__init__(*args, **kwargs)
        self.contribution.choices = ([('', _("Please select a contribution"))] +
                                     [(contrib.id, contrib.title) for contrib in self.event.getContributionList()])
        self.session.choices = ([('', _("Please select a session"))] +
                                [(session.id, session.title) for session in self.event.getSessionList()])
        self.linking._form = self

    def validate_name(self, field):
        if field.data and VCRoom.find_first(name=field.data):
            raise ValidationError(_("There is already a room with this name"))

    def validate_moderator(self, field):
        from indico_vc_vidyo.plugin import VidyoPlugin
        avatar = retrieve_principal(field.data)
        if not avatar:
            raise ValidationError(_("Unable to find this user in Indico."))
        authenticators = (a.strip() for a in VidyoPlugin.settings.get('authenticators').split(','))
        logins = next((identity.getLogin()
                       for auth in authenticators
                       for identity in avatar.getIdentityByAuthenticatorId(auth)), None)
        if not logins:
            raise ValidationError(_("This user does not have a suitable account to use Vidyo."))
