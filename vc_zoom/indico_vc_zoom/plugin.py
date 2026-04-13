# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import after_this_request, flash, g, has_request_context, request, session
from markupsafe import escape
from requests.exceptions import HTTPError
from sqlalchemy.orm.attributes import flag_modified
from wtforms.fields import BooleanField, TextAreaField, URLField
from wtforms.fields.simple import StringField
from wtforms.validators import URL, DataRequired, Optional, ValidationError

from indico.core import signals
from indico.core.auth import multipass
from indico.core.db import db
from indico.core.errors import UserValueError
from indico.core.plugins import IndicoPlugin, render_plugin_template, url_for_plugin
from indico.modules.events.registration.models.registrations import RegistrationState
from indico.modules.events.views import WPConferenceDisplay, WPSimpleEventDisplay
from indico.modules.logs import EventLogRealm, LogKind
from indico.modules.vc import VCPluginMixin, VCPluginSettingsFormBase
from indico.modules.vc.exceptions import VCRoomError, VCRoomNotFoundError
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomStatus
from indico.modules.vc.views import WPVCEventPage, WPVCManageEvent
from indico.util.user import principal_from_identifier
from indico.web.forms.fields import IndicoEnumSelectField, IndicoPasswordField, TextListField
from indico.web.forms.validators import HiddenUnless
from indico.web.forms.widgets import SwitchWidget, TinyMCEWidget

from indico_vc_zoom import _
from indico_vc_zoom.api import ZoomIndicoClient
from indico_vc_zoom.api.client import get_zoom_scopes, get_zoom_token
from indico_vc_zoom.blueprint import blueprint
from indico_vc_zoom.cli import cli
from indico_vc_zoom.forms import VCRoomAttachForm, VCRoomForm
from indico_vc_zoom.notifications import notify_host_start_url
from indico_vc_zoom.task import refresh_meetings
from indico_vc_zoom.util import (UserLookupMode, ZoomMeetingType, fetch_zoom_meeting, find_enterprise_email,
                                 gen_random_password, get_alt_host_emails, get_schedule_args, get_url_data_args,
                                 process_alternative_hosts, update_zoom_meeting)


AUTO_REGISTRATION_MEETING_SCOPES = ('meeting:read:list_registrants:admin', 'meeting:write:registrant:admin',
                                    'meeting:update:registrant_status:admin')
AUTO_REGISTRATION_LEGACY_MEETING_SCOPES = ('meeting:read:admin', 'meeting:write:admin')
AUTO_REGISTRATION_WEBINAR_SCOPES = ('webinar:read:list_registrants:admin', 'webinar:write:registrant:admin',
                                    'webinar:update:registrant_status:admin')
AUTO_REGISTRATION_LEGACY_WEBINAR_SCOPES = ('webinar:read:admin', 'webinar:write:admin')
# Zoom may return broad webinar scopes in the token instead of the granular registrant ones
AUTO_REGISTRATION_BROAD_WEBINAR_SCOPES = ('webinar:read:webinar:admin', 'webinar:write:webinar:admin')
AUTO_REGISTRATION_SCOPE_OPTIONS = {
    'meeting': (frozenset(AUTO_REGISTRATION_MEETING_SCOPES), frozenset(AUTO_REGISTRATION_LEGACY_MEETING_SCOPES)),
    'webinar': (frozenset(AUTO_REGISTRATION_WEBINAR_SCOPES), frozenset(AUTO_REGISTRATION_LEGACY_WEBINAR_SCOPES),
                frozenset(AUTO_REGISTRATION_BROAD_WEBINAR_SCOPES)),
}
# Limited to 30 by Zoom API.
# See https://developers.zoom.us/docs/api/meetings/#tag/invitation--registration/post/meetings/{meetingId}/registrants
BATCH_REGISTRANTS_MAX = 30


def _format_zoom_scopes(scopes):
    return ', '.join(f'"{scope}"' for scope in scopes)


def _has_required_zoom_scopes(granted_scopes, scope_options):
    return any(required_scopes <= granted_scopes for required_scopes in scope_options)


def _get_missing_auto_registration_scopes(granted_scopes, *, allow_webinars):
    missing_scopes = []
    keys = ('meeting', 'webinar') if allow_webinars else ('meeting',)
    for key in keys:
        scope_options = AUTO_REGISTRATION_SCOPE_OPTIONS[key]
        if not _has_required_zoom_scopes(granted_scopes, scope_options):
            best_missing = min((required - granted_scopes for required in scope_options), key=len)
            missing_scopes.extend(sorted(best_missing))
    return tuple(missing_scopes)


class PluginSettingsForm(VCPluginSettingsFormBase):
    _fieldsets = [
        (_('API Credentials'), ['account_id', 'client_id', 'client_secret', 'webhook_token']),
        (_('Zoom Account'), ['user_lookup_mode', 'email_domains', 'authenticators', 'enterprise_domain',
                             'allow_webinars', 'allow_language_interpretation', 'allow_auto_register', 'phone_link']),
        (_('Room Settings'), ['mute_audio', 'mute_host_video', 'mute_participant_video', 'join_before_host',
                              'waiting_room']),
        (_('Notifications'), ['creation_email_footer', 'send_host_url', 'notification_emails']),
        (_('Access'), ['managers', 'acl'])
    ]

    account_id = StringField(_('Account ID'))
    client_id = StringField(_('Client ID'))
    client_secret = IndicoPasswordField(_('Client Secret'), toggle=True)
    webhook_token = IndicoPasswordField(_('Webhook Secret Token'), toggle=True,
                                        description=_('Specify the "Secret Token" of your Zoom Webhook if you want '
                                                      'live updates in case of modified/deleted Zoom meetings.'))

    user_lookup_mode = IndicoEnumSelectField(_('User lookup mode'), [DataRequired()], enum=UserLookupMode,
                                             description=_('Specify how Indico should look up the zoom user that '
                                                           'corresponds to an Indico user.'))

    email_domains = TextListField(_('E-mail domains'),
                                  [HiddenUnless('user_lookup_mode', UserLookupMode.email_domains), DataRequired()],
                                  description=_('List of e-mail domains which can use the Zoom API. Indico attempts '
                                                'to find Zoom accounts using all email addresses of a user which use '
                                                'those domains.'))

    authenticators = TextListField(_('Indico identity providers'),
                                   [HiddenUnless('user_lookup_mode', UserLookupMode.authenticators), DataRequired()],
                                   description=_('Identity providers from which to get usernames. '
                                                 'Indico queries those providers using the email addresses of the user '
                                                 'and attempts to find Zoom accounts having an email address with the '
                                                 'format username@enterprise-domain.'))

    enterprise_domain = StringField(_('Enterprise domain'),
                                    [HiddenUnless('user_lookup_mode', UserLookupMode.authenticators), DataRequired()],
                                    description=_('The domain name used together with the usernames from the Indico '
                                                  'identity provider'))

    allow_webinars = BooleanField(_('Allow Webinars (Experimental)'),
                                  widget=SwitchWidget(),
                                  description=_('Allow webinars to be created through Indico. Use at your own risk.'))

    allow_language_interpretation = BooleanField(_('Allow Language Interpretation'),
                                                 widget=SwitchWidget(),
                                                 description=_('Allow enabling language interpretation for meetings '
                                                               'and webinars.'))

    allow_auto_register = BooleanField(_('Allow automatic registration'),
                                      widget=SwitchWidget(),
                                      description=_('Allow event managers to enable automatic Zoom registration on '
                                                    'individual meetings/webinars. Requires additional Zoom API '
                                                    'scopes; see the '
                                                    '<a href="https://github.com/indico/indico-plugins/tree/master/'
                                                    'vc_zoom#zoom-server-to-server-oauth">plugin README</a> '
                                                    'for details.'))

    mute_audio = BooleanField(_('Mute audio'),
                              widget=SwitchWidget(),
                              description=_('Participants will join the meeting muted by default '))

    mute_host_video = BooleanField(_('Mute video (host)'),
                                   widget=SwitchWidget(),
                                   description=_('The host will join the meeting with video disabled'))

    mute_participant_video = BooleanField(_('Mute video (participants)'),
                                          widget=SwitchWidget(),
                                          description=_('Participants will join the meeting with video disabled'))

    join_before_host = BooleanField(_('Join Before Host'),
                                    widget=SwitchWidget(),
                                    description=_('Allow participants to join the meeting before the host starts the '
                                                  'meeting. Only used for scheduled or recurring meetings.'))

    waiting_room = BooleanField(_('Waiting room'),
                                widget=SwitchWidget(),
                                description=_('Participants may be kept in a waiting room by the host'))

    creation_email_footer = TextAreaField(_('Creation email footer'), widget=TinyMCEWidget(),
                                          description=_('Footer to append to emails sent upon creation of a Zoom '
                                                        'meeting'))

    send_host_url = BooleanField(_('Send host URL'),
                                 widget=SwitchWidget(),
                                 description=_('Whether to send an e-mail with the Host URL to the meeting host upon '
                                               'creation of a meeting'))

    phone_link = URLField(_('Join via phone'), [Optional(), URL()],
                          description=_('Link to instructions on joining a meeting via phone'))

    def validate_authenticators(self, field):
        invalid = set(field.data) - set(multipass.identity_providers)
        if invalid:
            raise ValidationError(_('Invalid identity providers: {}').format(escape(', '.join(invalid))))

    def _get_zoom_config(self):
        return {
            'account_id': self.account_id.data,
            'client_id': self.client_id.data,
            'client_secret': self.client_secret.data,
        }

    def validate_allow_auto_register(self, field):
        if not field.data:
            return
        config = self._get_zoom_config()
        if not all(config.values()):
            return
        if not (scopes := get_zoom_scopes(config)):
            return
        if missing_scopes := _get_missing_auto_registration_scopes(scopes, allow_webinars=self.allow_webinars.data):
            raise ValidationError(
                _('The Zoom app is missing the required scopes for automatic registration. '
                  'Please add: {}.').format(_format_zoom_scopes(missing_scopes))
            )

    def validate_client_secret(self, field):
        config = self._get_zoom_config()
        if not all(config.values()):
            flash(_('Zoom credentials not set; the plugin will not work correctly'), 'error')
            return

        got_access_token, url, msg = get_zoom_token(config, for_config_check=True)
        if got_access_token:
            flash(_('Successfully got a Zoom token ({}); using API URL {}').format(msg, url), 'info')
            return
        raise ValidationError(_('Could not get Zoom token: {}').format(msg))


class ZoomPlugin(VCPluginMixin, IndicoPlugin):
    """Zoom

    Zoom Plugin for Indico.
    """

    configurable = True
    settings_form = PluginSettingsForm
    vc_room_form = VCRoomForm
    vc_room_attach_form = VCRoomAttachForm
    friendly_name = 'Zoom'
    default_settings = VCPluginMixin.default_settings | {
        'account_id': '',
        'client_id': '',
        'client_secret': '',
        'webhook_token': '',
        'user_lookup_mode': UserLookupMode.email_domains,
        'email_domains': [],
        'authenticators': [],
        'enterprise_domain': '',
        'allow_webinars': False,
        'allow_language_interpretation': False,
        'allow_auto_register': False,
        'mute_host_video': True,
        'mute_audio': True,
        'mute_participant_video': True,
        'join_before_host': True,
        'waiting_room': False,
        'creation_email_footer': None,
        'send_host_url': False,
        'phone_link': '',
    }

    def init(self):
        super().init()
        self.connect(signals.plugin.cli, self._extend_indico_cli)
        self.connect(signals.event.times_changed, self._check_meetings)
        self.connect(signals.event.metadata_postprocess, self._event_metadata_postprocess, sender='ical-export')
        self.connect(signals.event.registration_created, self._registration_created)
        self.connect(signals.event.registration_deleted, self._registration_deleted)
        self.connect(signals.event.registration_state_updated, self._registration_state_updated)
        self.connect(signals.event.registration_form_deleted, self._registration_form_deleted)
        self.connect(signals.vc.vc_room_created, self._vc_room_created)
        self.connect(signals.core.after_process, self._flush_pending_registrations)
        self.template_hook('event-vc-room-list-item-labels', self._render_vc_room_labels)
        for wp in (WPSimpleEventDisplay, WPVCEventPage, WPVCManageEvent, WPConferenceDisplay):
            self.inject_bundle('main.js', wp)
            self.inject_bundle('main.css', wp)

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/zoom_logo.svg')

    @property
    def icon_url(self):
        return url_for_plugin(self.name + '.static', filename='images/zoom_icon.svg')

    def create_form(self, event, existing_vc_room=None, existing_event_vc_room=None):
        """Override the default room form creation mechanism."""
        if existing_vc_room and request.method != 'POST':
            try:
                self.refresh_room(existing_vc_room, event)
            except VCRoomNotFoundError as exc:
                raise UserValueError(str(exc))
            except VCRoomError:
                # maybe a temporary issue - we just keep going and fail when saving in
                # case it's something more persistent
                pass

        form = super().create_form(
            event,
            existing_vc_room=existing_vc_room,
            existing_event_vc_room=existing_event_vc_room
        )

        if existing_vc_room:
            form.host_choice.render_kw = {'disabled': True}
            form.host_user.render_kw = {'disabled': True}
            if self.settings.get('allow_webinars'):
                # if we're editing a VC room, we will not allow the meeting type to be changed
                form.meeting_type.render_kw = {'disabled': True}

                if form.data['meeting_type'] == 'webinar':
                    # webinar hosts cannot be changed through the API
                    form.host_choice.render_kw = {'disabled': True}
                    form.host_user.render_kw = {'disabled': True}
        elif not form.is_submitted():
            form.password.data = gen_random_password()
        return form

    def get_extra_delete_msg(self, vc_room, event_vc_room):
        host = principal_from_identifier(vc_room.data['host'], require_user_token=False)
        if host == session.user or len(vc_room.events) <= 1:
            return ''
        return render_plugin_template('vc_zoom:extra_delete_msg.html', host=host.full_name)

    def _extend_indico_cli(self, sender, **kwargs):
        return cli

    def update_data_association(self, event, vc_room, room_assoc, data):
        # XXX: This feels slightly hacky. Maybe we should change the API on the core?
        association_is_new = room_assoc.vc_room is None

        assoc_has_changed = super().update_data_association(event, vc_room, room_assoc, data)

        if vc_room.data:
            try:
                if association_is_new:
                    self.refresh_room(vc_room, event)
                    is_webinar = vc_room.data.get('meeting_type') == 'webinar'
                    if vc_room.data.get('registration_required'):
                        raise UserValueError(
                            _('The meeting "{}" is using Zoom registration and thus cannot be attached to another '
                              'event').format(vc_room.name)
                        )
                    if vc_room.data.get('auto_register'):
                        raise UserValueError(
                            _('The meeting "{}" has automatic registration enabled and cannot be attached to another '
                              'event').format(vc_room.name)
                        )
                    # this means we are updating an existing meeting with a new vc_room-event association
                    update_zoom_meeting(vc_room.data['zoom_id'], {
                        'start_time': None,
                        'duration': None,
                        'type': (
                            ZoomMeetingType.recurring_webinar_no_time
                            if is_webinar
                            else ZoomMeetingType.recurring_meeting_no_time
                        )
                    }, is_webinar=is_webinar)
                elif assoc_has_changed:
                    # the booking should now be linked to something else
                    new_schedule_args = (get_schedule_args(room_assoc.link_object)
                                         if room_assoc.link_object.start_dt
                                         else {})
                    meeting, is_webinar = fetch_zoom_meeting(vc_room)
                    current_schedule_args = {k: meeting[k] for k in ('start_time', 'duration') if k in meeting}

                    # check whether the start time / duration of the scheduled meeting differs
                    if new_schedule_args != current_schedule_args:
                        if new_schedule_args:
                            update_zoom_meeting(vc_room.data['zoom_id'], new_schedule_args, is_webinar=is_webinar)
                        else:
                            update_zoom_meeting(vc_room.data['zoom_id'], {
                                'start_time': None,
                                'duration': None,
                                'type': (
                                    ZoomMeetingType.recurring_webinar_no_time
                                    if is_webinar
                                    else ZoomMeetingType.recurring_meeting_no_time
                                )
                            }, is_webinar=is_webinar)
            except VCRoomNotFoundError as exc:
                raise UserValueError(str(exc)) from exc

        room_assoc.data['password_visibility'] = data.pop('password_visibility')
        flag_modified(room_assoc, 'data')

        return assoc_has_changed

    def update_data_vc_room(self, vc_room, data, is_new=False):
        super().update_data_vc_room(vc_room, data, is_new=is_new)
        fields = {'description', 'password', 'auto_register'}

        # we may end up not getting a meeting_type from the form
        # (i.e. webinars are disabled)
        data.setdefault('meeting_type', 'regular' if is_new else vc_room.data['meeting_type'])

        if data['meeting_type'] == 'webinar':
            fields |= {'mute_host_video', 'language_interpretation', 'interpreters'}
            if is_new:
                fields |= {'host', 'meeting_type'}
        else:
            fields |= {
                'meeting_type', 'host', 'mute_audio', 'mute_participant_video', 'mute_host_video', 'join_before_host',
                'waiting_room', 'language_interpretation', 'interpreters'
            }

        for key in fields:
            if key in data:
                vc_room.data[key] = data.pop(key)

        flag_modified(vc_room, 'data')

    def create_room(self, vc_room, event):
        """Create a new Zoom meeting for an event, given a VC room.

        In order to create the Zoom meeting, the function will try to get
        a valid e-mail address for the user in question, which can be
        use with the Zoom API.

        :param vc_room: the VC room from which to create the Zoom meeting
        :param event: the event to the Zoom meeting will be attached
        """
        client = ZoomIndicoClient()
        host = principal_from_identifier(vc_room.data['host'], require_user_token=False)
        host_email = find_enterprise_email(host)

        # get the object that this booking is linked to
        vc_room_assoc = vc_room.events[0]
        link_obj = vc_room_assoc.link_object
        is_webinar = vc_room.data.setdefault('meeting_type', 'regular') == 'webinar'
        scheduling_args = get_schedule_args(link_obj) if link_obj.start_dt else {}

        try:
            settings = {
                'use_pmi': False,
                'host_video': not vc_room.data['mute_host_video'],
                'language_interpretation': self._build_language_interpretation_settings(vc_room)
            }

            kwargs = {}
            if is_webinar:
                kwargs['type'] = (ZoomMeetingType.webinar
                                  if scheduling_args
                                  else ZoomMeetingType.recurring_webinar_no_time)
                settings['alternative_hosts'] = host_email
            else:
                kwargs = {
                    'type': (
                        ZoomMeetingType.scheduled_meeting
                        if scheduling_args
                        else ZoomMeetingType.recurring_meeting_no_time
                    ),
                    'schedule_for': host_email
                }
                settings.update({
                    'mute_upon_entry': vc_room.data['mute_audio'],
                    'participant_video': not vc_room.data['mute_participant_video'],
                    'waiting_room': vc_room.data['waiting_room'],
                    'join_before_host': self.settings.get('join_before_host'),
                })
                if vc_room.data.get('auto_register'):
                    settings['approval_type'] = 0

            kwargs.update({
                'topic': vc_room.name,
                'agenda': vc_room.data['description'],
                'password': vc_room.data['password'],
                'timezone': event.timezone,
                'settings': settings
            })
            kwargs.update(scheduling_args)
            if is_webinar:
                meeting_obj = client.create_webinar(host_email, **kwargs)
            else:
                meeting_obj = client.create_meeting(host_email, **kwargs)
        except HTTPError as e:
            self.logger.exception('Error creating Zoom meeting: %s', e.response.content)
            raise VCRoomError(_('Could not create the meeting in Zoom. Please contact support if the error persists'))

        vc_room.data.update({
            'zoom_id': meeting_obj['id'],
            'start_url': meeting_obj['start_url'],
            'host': host.persistent_identifier,
            'alternative_hosts': process_alternative_hosts(meeting_obj['settings'].get('alternative_hosts', '')),
            'registration_required': meeting_obj['settings'].get('approval_type') != 2,
        })
        vc_room.data.update(get_url_data_args(meeting_obj['join_url']))
        flag_modified(vc_room, 'data')

        # e-mail Host URL to meeting host
        if self.settings.get('send_host_url'):
            notify_host_start_url(vc_room)

    def _build_language_interpretation_settings(self, vc_room):
        return {
            'enable': vc_room.data.get('language_interpretation', False),
            'interpreters': [
                {'email': x['email'], 'interpreter_languages': f"{x['src_lang']},{x['target_lang']}"}
                for x in (vc_room.data.get('interpreters') or [])
            ]
        }

    def update_room(self, vc_room, event):
        client = ZoomIndicoClient()
        zoom_meeting, is_webinar = fetch_zoom_meeting(vc_room, client=client)
        changes = {}

        if vc_room.name != zoom_meeting['topic']:
            changes['topic'] = vc_room.name

        if vc_room.data['description'] != zoom_meeting.get('agenda', ''):
            changes['agenda'] = vc_room.data['description']

        if vc_room.data['password'] != zoom_meeting['password']:
            changes['password'] = vc_room.data['password']

        zoom_meeting_settings = zoom_meeting['settings']
        if vc_room.data['mute_host_video'] == zoom_meeting_settings['host_video']:
            changes.setdefault('settings', {})['host_video'] = not vc_room.data['mute_host_video']

        zoom_language_interpretation = zoom_meeting_settings.get('language_interpretation', {})
        zoom_interpreters = [
            {
                'email': x['email'],
                'src_lang': x['interpreter_languages'].split(',')[0],
                'target_lang': x['interpreter_languages'].split(',')[1],
            }
            for x in zoom_language_interpretation.get('interpreters', [])
        ]
        local_interpreters = vc_room.data.get('interpreters') or []
        interpretation_changed = (
            vc_room.data.get('language_interpretation', False)
            != zoom_language_interpretation.get('enable', False)
        )
        interpreters_changed = local_interpreters != zoom_interpreters
        if interpretation_changed or interpreters_changed:
            changes.setdefault('settings', {})['language_interpretation'] = (
                self._build_language_interpretation_settings(vc_room)
            )

        alternative_hosts = process_alternative_hosts(zoom_meeting_settings.get('alternative_hosts', ''))
        if vc_room.data['alternative_hosts'] != alternative_hosts:
            new_alt_host_emails = get_alt_host_emails(vc_room.data['alternative_hosts'])
            changes.setdefault('settings', {})['alternative_hosts'] = ','.join(new_alt_host_emails)

        if not is_webinar:
            if vc_room.data['mute_audio'] != zoom_meeting_settings['mute_upon_entry']:
                changes.setdefault('settings', {})['mute_upon_entry'] = vc_room.data['mute_audio']
            if vc_room.data['mute_participant_video'] == zoom_meeting_settings['participant_video']:
                changes.setdefault('settings', {})['participant_video'] = not vc_room.data['mute_participant_video']
            if vc_room.data['waiting_room'] != zoom_meeting_settings['waiting_room']:
                changes.setdefault('settings', {})['waiting_room'] = vc_room.data['waiting_room']

        if changes:
            update_zoom_meeting(vc_room.data['zoom_id'], changes, is_webinar=is_webinar)
            # always refresh meeting URL (it may have changed if password changed)
            zoom_meeting, _is_webinar = fetch_zoom_meeting(vc_room, client=client)
            vc_room.data.update(get_url_data_args(zoom_meeting['join_url']))

    def refresh_room(self, vc_room, event):
        is_webinar = vc_room.data['meeting_type'] == 'webinar'
        zoom_meeting, is_really_webinar = fetch_zoom_meeting(vc_room)
        if is_webinar != is_really_webinar:
            vc_room.data['meeting_type'] = 'webinar' if is_really_webinar else 'regular'
        vc_room.name = zoom_meeting['topic']
        vc_room.data.update({
            'description': zoom_meeting.get('agenda', ''),
            'zoom_id': zoom_meeting['id'],
            'password': zoom_meeting['password'],
            'mute_host_video': not zoom_meeting['settings']['host_video'],
            'language_interpretation': zoom_meeting['settings'].get('language_interpretation', {}).get('enable', False),
            'interpreters': [
                {'email': x['email'], 'src_lang': x['interpreter_languages'].split(',')[0],
                 'target_lang': x['interpreter_languages'].split(',')[1]}
                for x in zoom_meeting['settings'].get('language_interpretation', {}).get('interpreters', [])
            ],

            # these options will be empty for webinars
            'mute_audio': zoom_meeting['settings'].get('mute_upon_entry'),
            'mute_participant_video': not zoom_meeting['settings'].get('participant_video'),
            'waiting_room': zoom_meeting['settings'].get('waiting_room'),
            'alternative_hosts': process_alternative_hosts(zoom_meeting['settings'].get('alternative_hosts')),
            'registration_required': zoom_meeting['settings'].get('approval_type') != 2,
        })
        vc_room.data.update(get_url_data_args(zoom_meeting['join_url']))
        flag_modified(vc_room, 'data')

    def delete_room(self, vc_room, event, *, _is_webinar=False):
        client = ZoomIndicoClient()
        zoom_id = vc_room.data['zoom_id']

        try:
            if _is_webinar:
                client.delete_webinar(zoom_id)
            else:
                client.delete_meeting(zoom_id)
        except HTTPError as e:
            # if it's a webinar, delete that instead
            if not _is_webinar and e.response.status_code == 400 and e.response.json().get('code') == 3000:
                self.delete_room(vc_room, event, _is_webinar=True)
                return
            # if there's a 404, there is no problem, since the room is supposed to be gone anyway
            elif e.response.status_code == 404:
                if has_request_context():
                    flash(_("Meeting didn't exist in Zoom anymore"), 'warning')
            elif e.response.status_code == 400:
                # some sort of operational error on Zoom's side, deserves a specific error message
                raise VCRoomError(_('Zoom Error: "{}"').format(e.response.json()['message']))
            else:
                self.logger.error("Can't delete meeting")
                raise VCRoomError(_('Problem deleting Zoom meeting'))

    def clone_room(self, old_event_vc_room, link_object):
        vc_room = old_event_vc_room.vc_room
        has_only_one_association = len({assoc.event_id for assoc in vc_room.events}) == 1

        refreshed = g.setdefault('zoom_refreshed_rooms', set())
        deleted = False
        if vc_room not in refreshed:
            refreshed.add(vc_room)
            try:
                self.refresh_room(vc_room, old_event_vc_room.event)
            except VCRoomNotFoundError:
                deleted = True

        if deleted or vc_room.status == VCRoomStatus.deleted:
            # this check is needed in order to avoid multiple flashes
            if vc_room.status != VCRoomStatus.deleted:
                # mark room as deleted
                vc_room.status = VCRoomStatus.deleted
                flash(
                    _('The meeting "{}" no longer exists in Zoom and was removed from the event').format(vc_room.name),
                    'warning'
                )
            return None

        if vc_room.data.get('registration_required'):
            flash(_('The meeting "{}" is using Zoom registration and thus cannot be attached to the new event')
                  .format(vc_room.name), 'warning')
            return None

        if vc_room.data.get('auto_register'):
            flash(_('The meeting "{}" has automatic registration enabled and cannot be cloned to the new event')
                  .format(vc_room.name), 'warning')
            return None

        if has_only_one_association:
            is_webinar = vc_room.data.get('meeting_type', 'regular') == 'webinar'
            update_zoom_meeting(vc_room.data['zoom_id'], {
                'start_time': None,
                'duration': None,
                'type': (
                    ZoomMeetingType.recurring_webinar_no_time
                    if is_webinar
                    else ZoomMeetingType.recurring_meeting_no_time
                )
            }, is_webinar=is_webinar)

        # return the new association
        return super().clone_room(old_event_vc_room, link_object)

    def get_blueprints(self):
        return blueprint

    def get_vc_room_form_defaults(self, event):
        defaults = super().get_vc_room_form_defaults(event)
        auto_register_enabled = self.settings.get('allow_auto_register')
        defaults.update({
            'meeting_type': 'regular' if self.settings.get('allow_webinars') else None,
            'mute_audio': self.settings.get('mute_audio'),
            'mute_host_video': self.settings.get('mute_host_video'),
            'mute_participant_video': self.settings.get('mute_participant_video'),
            'waiting_room': self.settings.get('waiting_room'),
            'auto_register': auto_register_enabled,
            'language_interpretation': False,
            'interpreters': [],
            'host_choice': 'myself',
            'host_user': None,
            'password_visibility': 'no_one' if auto_register_enabled else 'logged_in'
        })
        return defaults

    def get_vc_room_attach_form_defaults(self, event):
        defaults = super().get_vc_room_attach_form_defaults(event)
        defaults['password_visibility'] = 'logged_in'  # noqa: S105
        return defaults

    def can_manage_vc_room(self, user, room):
        return (
            user == principal_from_identifier(room.data['host'], require_user_token=False) or
            super().can_manage_vc_room(user, room)
        )

    def _merge_users(self, target, source, **kwargs):
        super()._merge_users(target, source, **kwargs)
        for room in VCRoom.query.filter(
            VCRoom.type == self.service_name, VCRoom.data.contains({'host': source.persistent_identifier})
        ):
            room.data['host'] = target.persistent_identifier
            flag_modified(room, 'data')
        for room in VCRoom.query.filter(
            VCRoom.type == self.service_name,
            VCRoom.data.contains({'alternative_hosts': [source.persistent_identifier]}),
        ):
            room.data['alternative_hosts'].remove(source.persistent_identifier)
            room.data['alternative_hosts'].append(target.persistent_identifier)
            flag_modified(room, 'data')

    def get_notification_cc_list(self, action, vc_room, event):
        return {principal_from_identifier(vc_room.data['host'], require_user_token=False).email}

    def _check_meetings(self, sender, obj, **kwargs):
        zoom_rooms = [ass.vc_room for ass in getattr(obj, 'vc_room_associations', []) if ass.vc_room.type == 'zoom']
        if not zoom_rooms:
            return

        log_entry = obj.log(EventLogRealm.event, LogKind.change, 'Videoconference', 'Zoom schedule updated', data={
            'Meetings': ', '.join([f'{room.name} (ID: {room.id})' for room in zoom_rooms]),
            'Date': obj.start_dt.isoformat(),
            'State': 'pending'
        })

        @after_this_request
        def _launch_task(response):
            # only launch task if we ended up committing
            if log_entry in db.session:
                refresh_meetings.delay(zoom_rooms, obj, log_entry)
            return response

    def _render_vc_room_labels(self, event, vc_room, **kwargs):
        if vc_room.plugin != self:
            return
        return render_plugin_template('room_labels.html', vc_room=vc_room)

    def _event_metadata_postprocess(self, sender, event, data, user=None, skip_access_check=False, **kwargs):
        html = 'description' in kwargs.get('html_fields', ())
        items = []
        for assoc in event.vc_room_associations:
            if not assoc.show or assoc.vc_room.type != 'zoom':
                continue
            visibility = assoc.data.get('password_visibility', 'logged_in')
            if (
                (skip_access_check and visibility != 'no_one') or
                visibility == 'everyone' or
                (visibility == 'logged_in' and user is not None) or
                (visibility == 'registered' and user is not None and event.is_user_registered(user)) or
                event.can_manage(user)
            ):
                url = assoc.vc_room.data['url']
                if user is not None:
                    if personalized_url := self.get_personalized_join_url(assoc.vc_room, assoc, user):
                        url = personalized_url
                items.append((assoc.vc_room.name, url))
            elif visibility == 'no_one':
                # XXX: Not sure if showing this is useful, but on the event page we show the join link
                # with no passcode as well, so let's keep the logic identical here.
                items.append((assoc.vc_room.name, assoc.vc_room.data['public_url']))

        if not items:
            return

        if html:
            desc = render_plugin_template('vc_zoom:event_metadata_desc.html', items=items)
            return {'description': data['description'] + f'\n{desc}'}

        if len(items) == 1:
            urls = [url for name, url in items]
            desc = f'Zoom: {urls[0]}'
        else:
            urls = [f'- {name}: {url}' for name, url in items]
            desc = 'Zoom:\n' + '\n'.join(urls)

        return {'description': (data['description'] + '\n\n' + desc).strip()}

    def _registration_created(self, registration, **kwargs):
        self._queue_registration_sync(registration, remove=False)

    def _registration_deleted(self, registration, **kwargs):
        self._queue_registration_sync(registration, remove=True)

    def _registration_state_updated(self, registration, **kwargs):
        if registration.state == RegistrationState.complete:
            self._queue_registration_sync(registration, remove=False)
        elif registration.state == RegistrationState.withdrawn:
            self._queue_registration_sync(registration, remove=True)

    def _registration_form_deleted(self, registration_form, **kwargs):
        for registration in registration_form.active_registrations:
            self._queue_registration_sync(registration, remove=True)

    def _vc_room_created(self, vc_room, event, **kwargs):
        if vc_room.type != self.service_name or not self.settings.get('allow_auto_register'):
            return
        if not vc_room.data.get('auto_register'):
            return
        for regform in event.registration_forms:
            for registration in regform.active_registrations:
                if registration.state == RegistrationState.complete:
                    self._queue_registration_sync(registration, remove=False)

    def _get_registrant_email(self, registration):
        if registration.user:
            if enterprise_email := find_enterprise_email(registration.user):
                return enterprise_email.lower()
        return registration.email

    def _get_user_registration(self, event, user):
        from indico.modules.events.registration.models.forms import RegistrationForm
        from indico.modules.events.registration.models.registrations import Registration

        return (Registration.query.with_parent(event)
                .join(Registration.registration_form)
                .filter(Registration.user == user,
                        Registration.state == RegistrationState.complete,
                        ~Registration.is_deleted,
                        ~RegistrationForm.is_deleted)
                .first())

    def get_personalized_join_url(self, vc_room, event_vc_room, user):
        if user is None or vc_room.type != self.service_name or not self.settings.get('allow_auto_register'):
            return None
        if not vc_room.data.get('auto_register'):
            return None

        cache_key = None
        if has_request_context():
            cache_key = (vc_room.id, user.id)
            cached_urls = g.setdefault('zoom_personalized_join_urls', {})
            if cache_key in cached_urls:
                return cached_urls[cache_key]

        registration = self._get_user_registration(event_vc_room.event, user)
        if registration is None:
            result = None
        else:
            email = self._get_registrant_email(registration)
            is_webinar = vc_room.data.get('meeting_type') == 'webinar'
            try:
                registrant = self._find_zoom_registrants(ZoomIndicoClient(), vc_room, {email}).get(email)
            except HTTPError:
                zoom_type = 'webinar' if is_webinar else 'meeting'
                self.logger.warning(f'Could not fetch registrants for Zoom {zoom_type} %s',  # noqa: G004
                                    vc_room.data['zoom_id'])
                result = None
            else:
                result = registrant.get('join_url') if registrant else None

        if cache_key is not None:
            cached_urls[cache_key] = result
        return result

    def _queue_registration_sync(self, registration, *, remove):
        if not self.settings.get('allow_auto_register'):
            return
        pending = g.setdefault('zoom_pending_registrations', {})
        pending[registration.id] = (registration, remove)

    def _flush_pending_registrations(self, sender, **kwargs):
        if not (pending := g.pop('zoom_pending_registrations', None)):
            return

        if not (room_ops := self._collect_room_ops(pending)):
            return

        client = ZoomIndicoClient()
        for zoom_id, ops in room_ops.items():
            is_webinar = ops['vc_room'].data.get('meeting_type') == 'webinar'
            self._add_registrants(client, zoom_id, ops['add'], is_webinar)
            self._remove_registrants(client, zoom_id, ops['vc_room'], ops['remove'], is_webinar)

    def _collect_room_ops(self, pending):
        pending_remove_ids = {reg.id for reg, remove in pending.values() if remove}
        pending_add_ids = {reg.id for reg, remove in pending.values() if not remove}
        room_ops = {}
        for registration, remove in pending.values():
            event = registration.event or registration.registration_form.event
            if event is None:
                continue
            zoom_rooms = [assoc.vc_room for assoc in event.vc_room_associations
                          if assoc.vc_room.type == self.service_name
                          and assoc.vc_room.data.get('auto_register')]
            if not zoom_rooms:
                continue

            is_active = registration.state == RegistrationState.complete
            should_add = not remove and is_active
            email = self._get_registrant_email(registration)

            for vc_room in zoom_rooms:
                if should_add and self._has_other_active_room_registration(vc_room, email, pending_add_ids):
                    continue
                if not should_add and self._has_other_active_room_registration(vc_room, email, pending_remove_ids):
                    continue

                zoom_id = vc_room.data['zoom_id']
                if zoom_id not in room_ops:
                    room_ops[zoom_id] = {'add': {}, 'remove': set(), 'vc_room': vc_room}

                if should_add:
                    room_ops[zoom_id]['add'][email] = {
                        'email': email,
                        'first_name': registration.first_name,
                        'last_name': registration.last_name,
                    }
                else:
                    room_ops[zoom_id]['remove'].add(email)
        for ops in room_ops.values():
            ops['add'] = list(ops['add'].values())
        return room_ops

    def _has_other_active_room_registration(self, vc_room, email, exclude_ids):
        from indico.modules.events.models.events import Event
        from indico.modules.events.registration.models.forms import RegistrationForm
        from indico.modules.events.registration.models.registrations import Registration

        if not (event_ids := {assoc.event_id for assoc in vc_room.events}):
            return False

        query = (Registration.query
                 .join(Registration.registration_form)
                 .join(RegistrationForm.event)
                 .filter(RegistrationForm.event_id.in_(event_ids),
                         Registration.state == RegistrationState.complete,
                         ~Registration.is_deleted,
                         ~RegistrationForm.is_deleted,
                         ~Event.is_deleted))
        if exclude_ids:
            query = query.filter(Registration.id.notin_(exclude_ids))
        return any(self._get_registrant_email(registration) == email for registration in query)

    def _add_registrants(self, client, zoom_id, registrants, is_webinar):
        if not registrants:
            return
        if len(registrants) == 1:
            self._add_single_registrant(client, zoom_id, registrants[0], is_webinar)
        else:
            self._add_batch_registrants(client, zoom_id, registrants, is_webinar)

    def _add_single_registrant(self, client, zoom_id, reg_data, is_webinar):
        zoom_type = 'webinar' if is_webinar else 'meeting'
        data = {**reg_data, 'auto_approve': True}
        try:
            if is_webinar:
                client.add_webinar_registrant(zoom_id, data)
            else:
                client.add_meeting_registrant(zoom_id, data)
        except HTTPError:
            self.logger.warning(f'Could not add registrant %s to Zoom {zoom_type} %s',  # noqa: G004
                                reg_data['email'], zoom_id)
        else:
            self.logger.info(f'Added registrant %s to Zoom {zoom_type} %s',  # noqa: G004
                             reg_data['email'], zoom_id)

    def _add_batch_registrants(self, client, zoom_id, registrants, is_webinar):
        zoom_type = 'webinar' if is_webinar else 'meeting'
        batch_func = client.batch_webinar_registrants if is_webinar else client.batch_meeting_registrants
        for i in range(0, len(registrants), BATCH_REGISTRANTS_MAX):
            chunk = registrants[i:i + BATCH_REGISTRANTS_MAX]
            data = {'auto_approve': True, 'registrants': chunk}
            try:
                batch_func(zoom_id, data)
            except HTTPError:
                emails = ', '.join(r['email'] for r in chunk)
                self.logger.warning(f'Could not batch-add registrants to Zoom {zoom_type} %s: %s',  # noqa: G004
                                    zoom_id, emails)
            else:
                emails = ', '.join(r['email'] for r in chunk)
                self.logger.info(f'Batch-added registrants to Zoom {zoom_type} %s: %s',  # noqa: G004
                                 zoom_id, emails)

    def _remove_registrants(self, client, zoom_id, vc_room, emails, is_webinar):
        if not emails:
            return
        zoom_type = 'webinar' if is_webinar else 'meeting'
        try:
            registrant_map = self._find_zoom_registrant_ids(client, vc_room, emails)
            if not registrant_map:
                return
            status_data = {
                'action': 'cancel',
                'registrants': [{'id': rid, 'email': email}
                                for email, rid in registrant_map.items()]
            }
            if is_webinar:
                client.update_webinar_registrants_status(zoom_id, status_data)
            else:
                client.update_meeting_registrants_status(zoom_id, status_data)
        except HTTPError:
            self.logger.warning(f'Could not remove registrants from Zoom {zoom_type} %s',  # noqa: G004
                                zoom_id)
        else:
            self.logger.info(f'Removed registrants from Zoom {zoom_type} %s',  # noqa: G004
                             zoom_id)

    def _find_zoom_registrant_ids(self, client, vc_room, emails):
        registrants = self._find_zoom_registrants(client, vc_room, emails)
        return {email: registrant['id'] for email, registrant in registrants.items()}

    def _find_zoom_registrants(self, client, vc_room, emails):
        zoom_id = vc_room.data['zoom_id']
        is_webinar = vc_room.data.get('meeting_type') == 'webinar'
        list_func = client.list_webinar_registrants if is_webinar else client.list_meeting_registrants

        found = {}
        remaining = {e.lower() for e in emails}
        params = {'page_size': 300}
        while remaining:
            resp = list_func(zoom_id, **params)
            for r in resp.get('registrants', []):
                if r['email'].lower() in remaining:
                    found[r['email'].lower()] = r
                    remaining.discard(r['email'].lower())
            if not resp.get('next_page_token'):
                break
            params['next_page_token'] = resp['next_page_token']
        return found
