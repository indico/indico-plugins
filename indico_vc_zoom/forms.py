from __future__ import unicode_literals
from flask import session

from wtforms.fields.core import BooleanField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired, ValidationError

from indico.modules.vc.forms import VCRoomAttachFormBase, VCRoomFormBase
from indico.util.user import principal_from_identifier
from indico.web.forms.base import generated_data
from indico.web.forms.fields import IndicoRadioField, PrincipalField
from indico.web.forms.validators import HiddenUnless
from indico.web.forms.widgets import SwitchWidget

from indico_vc_zoom import _


class ZoomAdvancedFormMixin(object):
    # Advanced options (per event)

    password_visibility = IndicoRadioField(_("Password visibility"),
                                           description=_("Who should be able to know this meeting's password"),
                                           orientation='horizontal',
                                           choices=[
                                               ('everyone', _('Everyone')),
                                               ('logged_in', _('Logged-in users')),
                                               ('no_one', _("No one"))])


class VCRoomAttachForm(VCRoomAttachFormBase, ZoomAdvancedFormMixin):
    pass


class VCRoomForm(VCRoomFormBase, ZoomAdvancedFormMixin):
    """Contains all information concerning a Zoom booking."""

    advanced_fields = {'mute_audio', 'mute_host_video', 'mute_participant_video'} | VCRoomFormBase.advanced_fields

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
            owner = principal_from_identifier(defaults.owner)
            defaults.owner_choice = 'myself' if owner == session.user else 'someone_else'
            defaults.owner_user = None if owner == session.user else owner
        super(VCRoomForm, self).__init__(*args, **kwargs)

    @generated_data
    def owner(self):
        return session.user.identifier if self.owner_choice.data == 'myself' else self.owner_user.data.identifier

    def validate_owner_user(self, field):
        if not field.data:
            raise ValidationError(_("Unable to find this user in Indico."))
