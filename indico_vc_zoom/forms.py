

from __future__ import unicode_literals
from flask import session

from wtforms.fields.core import BooleanField
from wtforms.fields.simple import TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, Regexp, ValidationError

from indico.modules.vc.forms import VCRoomAttachFormBase, VCRoomFormBase
from indico.web.forms.base import generated_data
from indico.web.forms.fields import IndicoPasswordField, PrincipalField
from indico.web.forms.widgets import SwitchWidget

from indico_vc_zoom import _
from indico_vc_zoom.util import iter_user_identities, retrieve_principal


PIN_VALIDATORS = [Optional(), Length(min=3, max=10), Regexp(r'^\d+$', message=_("The PIN must be a number"))]


class ZoomAdvancedFormMixin(object):
    # Advanced options (per event)
    
    show_autojoin = BooleanField(_('Show Auto-join URL'),
                                 widget=SwitchWidget(),
                                 description=_("Show the auto-join URL on the event page"))
    show_phone_numbers = BooleanField(_('Show Phone Access numbers'),
                                      widget=SwitchWidget(),
                                      description=_("Show a link to the list of phone access numbers"))


class VCRoomAttachForm(VCRoomAttachFormBase, ZoomAdvancedFormMixin):
    pass


class VCRoomForm(VCRoomFormBase, ZoomAdvancedFormMixin):
    """Contains all information concerning a Zoom booking"""

    advanced_fields = {'show_autojoin', 'show_phone_numbers'} | VCRoomFormBase.advanced_fields
    skip_fields = advanced_fields | VCRoomFormBase.conditional_fields

    description = TextAreaField(_('Description'), [DataRequired()], description=_('The description of the room'))
    #owner_user = PrincipalField(_('Owner'), [DataRequired()], description=_('The owner of the room'))
    #owner_user = HiddenField(default=session.user)
    #moderation_pin = IndicoPasswordField(_('Moderation PIN'), PIN_VALIDATORS, toggle=True,
    #                                     description=_('Used to moderate the VC Room. Only digits allowed.'))
    #room_pin = IndicoPasswordField(_('Room PIN'), PIN_VALIDATORS, toggle=True,
    #                               description=_('Used to protect the access to the VC Room (leave blank for open '
    #                                             'access). Only digits allowed.'))
                               

    def __init__(self, *args, **kwargs):
        defaults = kwargs['obj']
        if defaults.owner_user is None and defaults.owner is not None:
            defaults.owner_user = retrieve_principal(defaults.owner)
        super(VCRoomForm, self).__init__(*args, **kwargs)

    #@generated_data
    #def owner(self):
    #    return self.owner_user.data.default

    def validate_owner_user(self, field):
        if not field.data:
            raise ValidationError(_("Unable to find this user in Indico."))
        #if not next(iter_user_identities(field.data), None):
        #    raise ValidationError(_("This user does not have a suitable account to use Zoom."))
