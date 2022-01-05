# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import session
from flask_pluginengine import current_plugin
from wtforms.fields import BooleanField, StringField
from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired, ValidationError

from indico.modules.vc.forms import VCRoomAttachFormBase, VCRoomFormBase
from indico.util.user import principal_from_identifier
from indico.web.forms.base import generated_data
from indico.web.forms.fields import IndicoRadioField, PrincipalField
from indico.web.forms.util import inject_validators
from indico.web.forms.validators import HiddenUnless, IndicoRegexp
from indico.web.forms.widgets import SwitchWidget

from indico_vc_zoom import _
from indico_vc_zoom.util import find_enterprise_email


class VCRoomAttachForm(VCRoomAttachFormBase):
    password_visibility = IndicoRadioField(_('Passcode visibility'),
                                           description=_("Who should be able to know this meeting's passcode"),
                                           orientation='horizontal',
                                           choices=[
                                               ('everyone', _('Everyone')),
                                               ('logged_in', _('Logged-in users')),
                                               ('registered', _('Registered participants')),
                                               ('no_one', _('No one'))])


class VCRoomForm(VCRoomFormBase):
    """Contains all information concerning a Zoom booking."""

    advanced_fields = {'mute_audio', 'mute_host_video', 'mute_participant_video'} | VCRoomFormBase.advanced_fields

    skip_fields = advanced_fields | VCRoomFormBase.conditional_fields

    meeting_type = IndicoRadioField(_('Meeting Type'),
                                    description=_('The type of Zoom meeting to be created'),
                                    orientation='horizontal',
                                    choices=[
                                        ('regular', _('Regular Meeting')),
                                        ('webinar', _('Webinar'))])

    host_choice = IndicoRadioField(_('Meeting Host'), [DataRequired()],
                                   choices=[('myself', _('Myself')), ('someone_else', _('Someone else'))])

    host_user = PrincipalField(_('User'),
                               [HiddenUnless('host_choice', 'someone_else'), DataRequired()])

    password = StringField(_('Passcode'),
                           [DataRequired(), IndicoRegexp(r'^\d{8,10}$')],
                           description=_('Meeting passcode (8-10 digits)'))

    password_visibility = IndicoRadioField(_('Passcode visibility'),
                                           description=_("Who should be able to know this meeting's passcode"),
                                           orientation='horizontal',
                                           choices=[
                                               ('everyone', _('Everyone')),
                                               ('logged_in', _('Logged-in users')),
                                               ('registered', _('Registered participants')),
                                               ('no_one', _('No one'))])

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

    description = TextAreaField(_('Description'), description=_('Optional description for this room'))

    def __init__(self, *args, **kwargs):
        defaults = kwargs['obj']
        if defaults.host_user is None and defaults.host is not None:
            host = principal_from_identifier(defaults.host)
            defaults.host_choice = 'myself' if host == session.user else 'someone_else'
            defaults.host_user = None if host == session.user else host

        allow_webinars = current_plugin.settings.get('allow_webinars')

        if allow_webinars:
            for field_name in {'mute_audio', 'mute_participant_video', 'waiting_room'}:
                inject_validators(self, field_name, [HiddenUnless('meeting_type', 'regular')])

        super().__init__(*args, **kwargs)

        if not allow_webinars:
            del self.meeting_type

    def validate_host_choice(self, field):
        if field.data == 'myself':
            self._check_zoom_user(session.user)

    def validate_host_user(self, field):
        if self.host_choice.data == 'someone_else':
            self._check_zoom_user(field.data)

    def _check_zoom_user(self, user):
        if find_enterprise_email(user) is None:
            raise ValidationError(_('This user has no Zoom account'))

    def validate_name(self, field):
        # Duplicate names are fine on Zoom
        pass

    @generated_data
    def host(self):
        if self.host_choice is None:
            return None
        elif self.host_choice.data == 'myself':
            return session.user.identifier
        else:
            return self.host_user.data.identifier if self.host_user.data else None
