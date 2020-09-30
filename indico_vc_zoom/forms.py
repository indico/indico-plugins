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


class VCRoomAttachForm(VCRoomAttachFormBase):
    password_visibility = IndicoRadioField(_("Password visibility"),
                                           description=_("Who should be able to know this meeting's password"),
                                           orientation='horizontal',
                                           choices=[
                                               ('everyone', _('Everyone')),
                                               ('logged_in', _('Logged-in users')),
                                               ('no_one', _("No one"))])


class VCRoomForm(VCRoomFormBase):
    """Contains all information concerning a Zoom booking."""

    advanced_fields = {'mute_audio', 'mute_host_video', 'mute_participant_video'} | VCRoomFormBase.advanced_fields

    skip_fields = advanced_fields | VCRoomFormBase.conditional_fields

    meeting_type = IndicoRadioField(_("Meeting Type"),
                                    description=_("The type of Zoom meeting ot be created"),
                                    orientation='horizontal',
                                    choices=[
                                        ('regular', _('Regular Meeting')),
                                        ('webinar', _('Webinar'))])

    host_choice = IndicoRadioField(_("Meeting Host"), [DataRequired()],
                                   choices=[('myself', _("Myself")), ('someone_else', _("Someone else"))])

    host_user = PrincipalField(_("User"),
                               [HiddenUnless('host_choice', 'someone_else'), DataRequired()])

    password_visibility = IndicoRadioField(_("Password visibility"),
                                           description=_("Who should be able to know this meeting's password"),
                                           orientation='horizontal',
                                           choices=[
                                               ('everyone', _('Everyone')),
                                               ('logged_in', _('Logged-in users')),
                                               ('no_one', _("No one"))])

    mute_audio = BooleanField(_('Mute audio'),
                              [HiddenUnless('meeting_type', 'regular')],
                              widget=SwitchWidget(),
                              description=_('Participants will join the VC room muted by default '))

    mute_host_video = BooleanField(_('Mute video (host)'),
                                   widget=SwitchWidget(),
                                   description=_('The host will join the VC room with video disabled'))

    mute_participant_video = BooleanField(_('Mute video (participants)'),
                                          [HiddenUnless('meeting_type', 'regular')],
                                          widget=SwitchWidget(),
                                          description=_('Participants will join the VC room with video disabled'))

    waiting_room = BooleanField(_('Waiting room'),
                                [HiddenUnless('meeting_type', 'regular')],
                                widget=SwitchWidget(),
                                description=_('Participants may be kept in a waiting room by the host'))

    description = TextAreaField(_('Description'), description=_('Optional description for this room'))

    def __init__(self, *args, **kwargs):
        defaults = kwargs['obj']
        if defaults.host_user is None and defaults.host is not None:
            host = principal_from_identifier(defaults.host)
            defaults.host_choice = 'myself' if host == session.user else 'someone_else'
            defaults.host_user = None if host == session.user else host
        super(VCRoomForm, self).__init__(*args, **kwargs)

    @generated_data
    def host(self):
        if self.host_choice is None:
            return None
        return session.user.identifier if self.host_choice.data == 'myself' else self.host_user.data.identifier

    def validate_host_user(self, field):
        if not field.data:
            raise ValidationError(_("Unable to find this user in Indico."))
