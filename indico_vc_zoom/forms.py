from __future__ import unicode_literals
from flask import session

from wtforms.fields.core import BooleanField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired, ValidationError

from indico.modules.vc.forms import VCRoomAttachFormBase, VCRoomFormBase
from indico.web.forms.base import generated_data
from indico.web.forms.fields import IndicoRadioField, PrincipalField
from indico.web.forms.validators import HiddenUnless
from indico.web.forms.widgets import SwitchWidget

from indico_vc_zoom import _
from indico_vc_zoom.util import retrieve_principal


class ZoomAdvancedFormMixin(object):
    # Advanced options (per event)

    show_password = BooleanField(_('Show Password'),
                                 widget=SwitchWidget(),
                                 description=_("Show the Zoom Room Password on the event page"))
    show_autojoin = BooleanField(_('Show Auto-join URL'),
                                 widget=SwitchWidget(),
                                 description=_("Show the auto-join URL on the event page"))
    show_phone_numbers = BooleanField(_('Show Phone Access numbers'),
                                      widget=SwitchWidget(),
                                      description=_("Show a link to the list of phone access numbers"))


class VCRoomAttachForm(VCRoomAttachFormBase, ZoomAdvancedFormMixin):
    pass


class VCRoomForm(VCRoomFormBase, ZoomAdvancedFormMixin):
    """Contains all information concerning a Zoom booking."""

    advanced_fields = {'show_password', 'show_autojoin', 'show_phone_numbers'} | VCRoomFormBase.advanced_fields
    skip_fields = advanced_fields | VCRoomFormBase.conditional_fields

    description = TextAreaField(_('Description'), description=_('The description of the room'))

    owner_choice = IndicoRadioField(_("Owner of Room"), [DataRequired()],
                                    choices=[('myself', _("Myself")), ('someone_else', _("Someone else"))])
    owner_user = PrincipalField(_("User"),
                                [HiddenUnless('owner_choice', 'someone_else'), DataRequired()])

    mute_audio = BooleanField(_('Mute audio'),
                              widget=SwitchWidget(),
                              description=_('Participants will join the VC room muted by default '))

    mute_host_video = BooleanField(_('Mute video (host)'),
                                   widget=SwitchWidget(),
                                   description=_('The host will join the VC room with video disabled'))

    mute_participant_video = BooleanField(_('Mute video (participants)'),
                                          widget=SwitchWidget(),
                                          description=_('Participants will join the VC room with video disabled'))

    waiting_room = BooleanField(_('Waiting room'),
                                widget=SwitchWidget(),
                                description=_('Participants may be kept in a waiting room by the host'))

    def __init__(self, *args, **kwargs):
        defaults = kwargs['obj']
        if defaults.owner_user is None and defaults.owner is not None:
            owner = retrieve_principal(defaults.owner)
            defaults.owner_choice = 'myself' if owner == session.user else 'someone_else'
            defaults.owner_user = None if owner == session.user else owner
        super(VCRoomForm, self).__init__(*args, **kwargs)

    @generated_data
    def owner(self):
        return session.user.as_principal if self.owner_choice.data == 'myself' else self.owner_user.data.as_principal

    def validate_owner_user(self, field):
        if not field.data:
            raise ValidationError(_("Unable to find this user in Indico."))
