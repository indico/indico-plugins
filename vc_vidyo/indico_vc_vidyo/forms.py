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

from wtforms.fields.core import BooleanField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp, ValidationError

from indico.modules.vc.forms import VCRoomAttachFormBase, VCRoomFormBase
from indico.web.forms.base import generated_data
from indico.web.forms.fields import IndicoPasswordField, PrincipalField
from indico.web.forms.widgets import SwitchWidget

from indico_vc_vidyo import _
from indico_vc_vidyo.util import iter_user_identities, retrieve_principal


PIN_VALIDATORS = [Optional(), Length(min=3, max=10), Regexp(r'^\d+$', message=_("The PIN must be a number"))]


class VidyoAdvancedFormMixin(object):
    # Advanced options (per event)
    show_pin = BooleanField(_('Show PIN'),
                            widget=SwitchWidget(),
                            description=_("Show the VC Room PIN on the event page (insecure!)"))
    show_autojoin = BooleanField(_('Show Auto-join URL'),
                                 widget=SwitchWidget(),
                                 description=_("Show the auto-join URL on the event page"))
    show_phone_numbers = BooleanField(_('Show Phone Access numbers'),
                                      widget=SwitchWidget(),
                                      description=_("Show a link to the list of phone access numbers"))


class VCRoomAttachForm(VCRoomAttachFormBase, VidyoAdvancedFormMixin):
    pass


class VCRoomForm(VCRoomFormBase, VidyoAdvancedFormMixin):
    """Contains all information concerning a Vidyo booking"""

    advanced_fields = {'show_pin', 'show_autojoin', 'show_phone_numbers'} | VCRoomFormBase.advanced_fields
    skip_fields = advanced_fields | VCRoomFormBase.conditional_fields

    description = TextAreaField(_('Description'), [DataRequired()], description=_('The description of the room'))
    owner_user = PrincipalField(_('Owner'), [DataRequired()], description=_('The owner of the room'))
    moderation_pin = IndicoPasswordField(_('Moderation PIN'), PIN_VALIDATORS, toggle=True,
                                         description=_('Used to moderate the VC Room. Only digits allowed.'))
    room_pin = IndicoPasswordField(_('Room PIN'), PIN_VALIDATORS, toggle=True,
                                   description=_('Used to protect the access to the VC Room (leave blank for open '
                                                 'access). Only digits allowed.'))
    auto_mute = BooleanField(_('Auto mute'),
                             widget=SwitchWidget(_('On'), _('Off')),
                             description=_('The VidyoDesktop clients will join the VC room muted by default '
                                           '(audio and video)'))

    def __init__(self, *args, **kwargs):
        defaults = kwargs['obj']
        if defaults.owner_user is None and defaults.owner is not None:
            defaults.owner_user = retrieve_principal(defaults.owner)
        super(VCRoomForm, self).__init__(*args, **kwargs)

    @generated_data
    def owner(self):
        return self.owner_user.data.as_principal

    def validate_owner_user(self, field):
        if not field.data:
            raise ValidationError(_("Unable to find this user in Indico."))
        if not next(iter_user_identities(field.data), None):
            raise ValidationError(_("This user does not have a suitable account to use Vidyo."))
