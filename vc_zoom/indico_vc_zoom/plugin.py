# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2025 CERN and ENEA
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
from indico_vc_zoom.api.client import get_zoom_token
from indico_vc_zoom.blueprint import blueprint
from indico_vc_zoom.cli import cli
from indico_vc_zoom.forms import VCRoomAttachForm, VCRoomForm
from indico_vc_zoom.notifications import notify_host_start_url
from indico_vc_zoom.task import refresh_meetings
from indico_vc_zoom.util import (UserLookupMode, ZoomMeetingType, fetch_zoom_meeting, find_enterprise_email,
                                 gen_random_password, get_alt_host_emails, get_schedule_args, get_url_data_args,
                                 process_alternative_hosts, update_zoom_meeting)


class PluginSettingsForm(VCPluginSettingsFormBase):
    _fieldsets = [
        (_('API Credentials'), ['account_id', 'client_id', 'client_secret', 'webhook_token']),
        (_('Zoom Account'), ['user_lookup_mode', 'email_domains', 'authenticators', 'enterprise_domain',
                             'allow_webinars', 'phone_link']),
        (_('Room Settings'), ['mute_audio', 'mute_host_video', 'mute_participant_video', 'join_before_host',
                              'waiting_room']),
        (_('Notifications'), ['creation_email_footer', 'send_host_url', 'notification_emails']),
        (_('Access'), ['managers', 'acl'])
    ]

    account_id = StringField(_('Account ID'), [])
    client_id = StringField(_('Client ID'), [])
    client_secret = IndicoPasswordField(_('Client Secret'), [], toggle=True)

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

    def validate_client_secret(self, field):
        account_id = self.account_id.data
        client_id = self.client_id.data
        client_secret = self.client_secret.data
        if not account_id or not client_id or not client_secret:
            flash(_('Zoom credentials not set; the plugin will not work correctly'), 'error')
            return

        ok, msg = get_zoom_token({'account_id': account_id, 'client_id': client_id, 'client_secret': client_secret},
                                 for_config_check=True)
        if ok:
            flash(_('Successfully got a Zoom token ({})').format(msg), 'info')
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
        fields = {'description', 'password'}

        # we may end up not getting a meeting_type from the form
        # (i.e. webinars are disabled)
        data.setdefault('meeting_type', 'regular' if is_new else vc_room.data['meeting_type'])

        if data['meeting_type'] == 'webinar':
            fields |= {'mute_host_video'}
            if is_new:
                fields |= {'host', 'meeting_type'}
        else:
            fields |= {
                'meeting_type', 'host', 'mute_audio', 'mute_participant_video', 'mute_host_video', 'join_before_host',
                'waiting_room'
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
                'host_video': not vc_room.data['mute_host_video'],
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
        defaults.update({
            'meeting_type': 'regular' if self.settings.get('allow_webinars') else None,
            'mute_audio': self.settings.get('mute_audio'),
            'mute_host_video': self.settings.get('mute_host_video'),
            'mute_participant_video': self.settings.get('mute_participant_video'),
            'waiting_room': self.settings.get('waiting_room'),
            'host_choice': 'myself',
            'host_user': None,
            'password_visibility': 'logged_in'
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
        urls = []
        if 'description' in kwargs.get('html_fields', ()):
            linebreak = '<br>\n'
            format_link = lambda name, url: f'<a href="{url}">{escape(name)}: {url}</a>'
        else:
            linebreak = '\n'
            format_link = lambda name, url: f'{name}: {url}'

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
                urls.append(format_link(assoc.vc_room.name, assoc.vc_room.data['url']))
            elif visibility == 'no_one':
                # XXX: Not sure if showing this is useful, but on the event page we show the join link
                # with no passcode as well, so let's keep the logic identical here.
                urls.append(format_link(assoc.vc_room.name, assoc.vc_room.data['public_url']))

        if urls:
            return {'description': (data['description'] + (linebreak * 2) + linebreak.join(urls)).strip()}
