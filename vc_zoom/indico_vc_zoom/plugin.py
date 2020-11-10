# This file is part of the Indico plugins.
# Copyright (C) 2020 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask import flash, session
from requests.exceptions import HTTPError
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.exceptions import Forbidden, NotFound
from wtforms.fields.core import BooleanField
from wtforms.fields import TextAreaField
from wtforms.fields.html5 import URLField
from wtforms.fields.simple import StringField
from wtforms.validators import DataRequired

from indico.core import signals
from indico.core.config import config
from indico.core.plugins import IndicoPlugin, render_plugin_template, url_for_plugin
from indico.modules.events.views import WPSimpleEventDisplay
from indico.modules.vc import VCPluginMixin, VCPluginSettingsFormBase
from indico.modules.vc.exceptions import VCRoomError
from indico.modules.vc.models.vc_rooms import VCRoom
from indico.modules.vc.views import WPVCEventPage, WPVCManageEvent
from indico.util.user import principal_from_identifier
from indico.web.forms.fields.simple import IndicoPasswordField
from indico.web.forms.widgets import CKEditorWidget, SwitchWidget
from indico.web.http_api.hooks.base import HTTPAPIHook

from indico_vc_zoom import _
from indico_vc_zoom.api import ZoomIndicoClient
from indico_vc_zoom.blueprint import blueprint
from indico_vc_zoom.cli import cli
from indico_vc_zoom.forms import VCRoomAttachForm, VCRoomForm
from indico_vc_zoom.http_api import DeleteVCRoomAPI
from indico_vc_zoom.notifications import notify_new_host, notify_host_start_url
from indico_vc_zoom.util import (fetch_zoom_meeting, find_enterprise_email, gen_random_password, get_schedule_args,
                                 update_zoom_meeting)


class PluginSettingsForm(VCPluginSettingsFormBase):
    api_key = StringField(_('API Key'), [DataRequired()])

    api_secret = IndicoPasswordField(_('API Secret'), [DataRequired()], toggle=True)

    email_domains = StringField(_('E-mail domains'), [DataRequired()],
                                description=_("Comma-separated list of e-mail domains which can use the Zoom API."))

    assistant_id = StringField(_('Assistant Zoom ID'), [DataRequired()],
                               description=_('Account to be used as owner of all rooms. It will get "assistant" '
                                             'privileges on all accounts for which it books rooms'))

    mute_audio = BooleanField(_('Mute audio'),
                              widget=SwitchWidget(),
                              description=_('Participants will join the VC room muted by default '))

    mute_host_video = BooleanField(_('Mute video (host)'),
                                   widget=SwitchWidget(),
                                   description=_('The host will join the VC room with video disabled'))

    mute_participant_video = BooleanField(_('Mute video (participants)'),
                                          widget=SwitchWidget(),
                                          description=_('Participants will join the VC room with video disabled'))

    join_before_host = BooleanField(_('Join Before Host'),
                                    widget=SwitchWidget(),
                                    description=_('Allow participants to join the meeting before the host starts the '
                                                  'meeting. Only used for scheduled or recurring meetings.'))

    waiting_room = BooleanField(_('Waiting room'),
                                widget=SwitchWidget(),
                                description=_('Participants may be kept in a waiting room by the host'))

    zoom_phone_link = URLField(_('ZoomVoice phone number'),
                               description=_('Link to the list of ZoomVoice phone numbers'))

    creation_email_footer = TextAreaField(_('Creation email footer'), widget=CKEditorWidget(),
                                          description=_('Footer to append to emails sent upon creation of a VC room'))

    send_host_url = BooleanField(_('Send host URL'),
                                 widget=SwitchWidget(),
                                 description=_('Whether to send an e-mail with the Host URL to the meeting host upon '
                                               'creation of a meeting'))


class ZoomPlugin(VCPluginMixin, IndicoPlugin):
    """Zoom

    Zoom Plugin for Indico."""

    configurable = True
    settings_form = PluginSettingsForm
    vc_room_form = VCRoomForm
    vc_room_attach_form = VCRoomAttachForm
    friendly_name = 'Zoom'

    def init(self):
        super(ZoomPlugin, self).init()
        self.connect(signals.plugin.cli, self._extend_indico_cli)
        self.connect(signals.event.times_changed, self._times_changed)
        self.template_hook('event-vc-room-list-item-labels', self._render_vc_room_labels)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.js', WPVCEventPage)
        self.inject_bundle('main.js', WPVCManageEvent)
        HTTPAPIHook.register(DeleteVCRoomAPI)

    @property
    def default_settings(self):
        return dict(VCPluginMixin.default_settings, **{
            'assistant_id': config.SUPPORT_EMAIL,
            'api_key': '',
            'api_secret': '',
            'email_domains': '',
            'mute_host_video': True,
            'mute_audio': True,
            'mute_participant_video': True,
            'join_before_host': True,
            'waiting_room': False,
            'zoom_phone_link': None,
            'creation_email_footer': None,
            'send_host_url': False
        })

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/zoom_logo.png')

    @property
    def icon_url(self):
        return url_for_plugin(self.name + '.static', filename='images/zoom_logo.png')

    def create_form(self, event, existing_vc_room=None, existing_event_vc_room=None):
        """Override the default room form creation mechanism."""
        form = super(ZoomPlugin, self).create_form(
            event,
            existing_vc_room=existing_vc_room,
            existing_event_vc_room=existing_event_vc_room
        )

        if existing_vc_room:
            # if we're editing a VC room, we will not allow the meeting type to be changed
            form.meeting_type.render_kw = {'disabled': True}

            if form.data['meeting_type'] == 'webinar':
                # webinar hosts cannot be changed through the API
                form.host_choice.render_kw = {'disabled': True}
                form.host_user.render_kw = {'disabled': True}

        return form

    def _extend_indico_cli(self, sender, **kwargs):
        return cli

    def update_data_association(self, event, vc_room, room_assoc, data):
        # XXX: This feels slightly hacky. Maybe we should change the API on the core?
        association_is_new = room_assoc.vc_room is None
        old_link = room_assoc.link_object
        super(ZoomPlugin, self).update_data_association(event, vc_room, room_assoc, data)

        if vc_room.data:
            # this is not a new room
            if association_is_new:
                # this means we are updating an existing meeting with a new vc_room-event association
                update_zoom_meeting(vc_room.data['zoom_id'], {
                    'start_time': None,
                    'duration': None,
                    'type': 3
                })
            elif room_assoc.link_object != old_link:
                # the booking should now be linked to something else
                new_schedule_args = get_schedule_args(room_assoc.link_object)
                meeting = fetch_zoom_meeting(vc_room)
                current_schedule_args = {k: meeting[k] for k in {'start_time', 'duration'}}

                # check whether the start time / duration of the scheduled meeting differs
                if new_schedule_args != current_schedule_args:
                    update_zoom_meeting(vc_room.data['zoom_id'], new_schedule_args)

        room_assoc.data['password_visibility'] = data.pop('password_visibility')
        flag_modified(room_assoc, 'data')

    def update_data_vc_room(self, vc_room, data, is_new=False):
        super(ZoomPlugin, self).update_data_vc_room(vc_room, data)
        fields = {'description'}
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

    def _check_indico_is_assistant(self, user_id):
        client = ZoomIndicoClient()
        assistant_id = self.settings.get('assistant_id')

        if user_id != assistant_id:
            try:
                assistants = {assist['email'] for assist in client.get_assistants_for_user(user_id)['assistants']}
            except HTTPError as e:
                if e.response.status_code == 404:
                    raise NotFound(_("No Zoom account found for this user"))
                self.logger.exception('Error getting assistants for account %s: %s', user_id, e.response.content)
                raise VCRoomError(_("Problem getting information about Zoom account"))
            if assistant_id not in assistants:
                client.add_assistant_to_user(user_id, assistant_id)

    def create_room(self, vc_room, event):
        """Create a new Zoom room for an event, given a VC room.

        In order to create the Zoom room, the function will try to get
        a valid e-mail address for the user in question, which can be
        use with the Zoom API.

        :param vc_room: the VC room from which to create the Zoom room
        :param event: the event to the Zoom room will be attached
        """
        client = ZoomIndicoClient()
        host = principal_from_identifier(vc_room.data['host'])
        host_email = find_enterprise_email(host)

        # get the object that this booking is linked to
        vc_room_assoc = vc_room.events[0]
        link_obj = vc_room_assoc.link_object
        is_webinar = vc_room.data['meeting_type'] == 'webinar'
        scheduling_args = get_schedule_args(link_obj) if link_obj.start_dt else {}

        self._check_indico_is_assistant(host_email)

        try:
            settings = {
                'host_video': vc_room.data['mute_host_video'],
            }

            kwargs = {}
            if is_webinar:
                kwargs = {
                    'type': 5 if scheduling_args else 6,
                    'host_email': host_email
                }
            else:
                kwargs = {
                    'type': 2 if scheduling_args else 3,
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
                'password': gen_random_password(),
                'timezone': event.timezone,
                'settings': settings
            })
            kwargs.update(scheduling_args)
            if is_webinar:
                meeting_obj = client.create_webinar(self.settings.get('assistant_id'), **kwargs)
            else:
                meeting_obj = client.create_meeting(self.settings.get('assistant_id'), **kwargs)
        except HTTPError as e:
            self.logger.exception('Error creating Zoom Room: %s', e.response.content)
            raise VCRoomError(_("Could not create the room in Zoom. Please contact support if the error persists"))

        vc_room.data.update({
            'zoom_id': unicode(meeting_obj['id']),
            'url': meeting_obj['join_url'],
            'public_url': meeting_obj['join_url'].split('?')[0],
            'start_url': meeting_obj['start_url'],
            'password': meeting_obj['password'],
            'host': host.identifier
        })

        flag_modified(vc_room, 'data')

        # e-mail Host URL to meeting host
        if self.settings.get('send_host_url'):
            notify_host_start_url(vc_room)

    def update_room(self, vc_room, event):
        client = ZoomIndicoClient()
        is_webinar = vc_room.data['meeting_type'] == 'webinar'
        zoom_meeting = fetch_zoom_meeting(vc_room, client=client, is_webinar=is_webinar)
        changes = {}

        host = principal_from_identifier(vc_room.data['host'])
        host_id = zoom_meeting['host_id']

        try:
            host_data = client.get_user(host_id)
        except HTTPError as e:
            self.logger.exception("Error retrieving user '%s': %s", host_id, e.response.content)
            raise VCRoomError(_("Can't get information about user. Please contact support if the error persists."))

        # host changed
        if host_data['email'] not in host.all_emails:
            email = find_enterprise_email(host)

            if not email:
                raise Forbidden(_("This user doesn't seem to have an associated Zoom account"))

            changes['host_email' if is_webinar else 'schedule_for'] = email
            self._check_indico_is_assistant(email)
            notify_new_host(session.user, vc_room)

        if vc_room.name != zoom_meeting['topic']:
            changes['topic'] = vc_room.name

        zoom_meeting_settings = zoom_meeting['settings']
        if vc_room.data['mute_host_video'] == zoom_meeting_settings['host_video']:
            changes.setdefault('settings', {})['host_video'] = not vc_room.data['mute_host_video']

        if not is_webinar:
            if vc_room.data['mute_audio'] != zoom_meeting_settings['mute_upon_entry']:
                changes.setdefault('settings', {})['mute_upon_entry'] = vc_room.data['mute_audio']
            if vc_room.data['mute_participant_video'] == zoom_meeting_settings['participant_video']:
                changes.setdefault('settings', {})['participant_video'] = not vc_room.data['mute_participant_video']
            if vc_room.data['waiting_room'] != zoom_meeting_settings['waiting_room']:
                changes.setdefault('settings', {})['waiting_room'] = vc_room.data['waiting_room']

        if changes:
            update_zoom_meeting(vc_room.data['zoom_id'], changes, is_webinar=is_webinar)

    def refresh_room(self, vc_room, event):
        is_webinar = vc_room.data['meeting_type'] == 'webinar'
        zoom_meeting = fetch_zoom_meeting(vc_room, is_webinar=is_webinar)
        vc_room.name = zoom_meeting['topic']
        vc_room.data.update({
            'url': zoom_meeting['join_url'],
            'public_url': zoom_meeting['join_url'].split('?')[0],
            'zoom_id': zoom_meeting['id']
        })
        flag_modified(vc_room, 'data')

    def delete_room(self, vc_room, event):
        client = ZoomIndicoClient()
        zoom_id = vc_room.data['zoom_id']
        is_webinar = vc_room.data['meeting_type'] == 'webinar'
        try:
            if is_webinar:
                client.delete_webinar(zoom_id)
            else:
                client.delete_meeting(zoom_id)
        except HTTPError as e:
            # if there's a 404, there is no problem, since the room is supposed to be gone anyway
            if not e.response.status_code == 404:
                self.logger.exception('Error getting Zoom Room: %s', e.response.content)
                raise VCRoomError(_("Problem fetching room from Zoom. Please contact support if the error persists."))

    def get_blueprints(self):
        return blueprint

    def get_vc_room_form_defaults(self, event):
        defaults = super(ZoomPlugin, self).get_vc_room_form_defaults(event)
        defaults.update({
            'meeting_type': 'regular',
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
        defaults = super(ZoomPlugin, self).get_vc_room_attach_form_defaults(event)
        defaults['password_visibility'] = 'logged_in'
        return defaults

    def can_manage_vc_room(self, user, room):
        return (
            user == principal_from_identifier(room.data['host']) or
            super(ZoomPlugin, self).can_manage_vc_room(user, room)
        )

    def _merge_users(self, target, source, **kwargs):
        super(ZoomPlugin, self)._merge_users(target, source, **kwargs)
        for room in VCRoom.query.filter(
            VCRoom.type == self.service_name, VCRoom.data.contains({'host': source.identifier})
        ):
            room.data['host'] = target.id
            flag_modified(room, 'data')

    def get_notification_cc_list(self, action, vc_room, event):
        return {principal_from_identifier(vc_room.data['host']).email}

    def _render_vc_room_labels(self, event, vc_room, **kwargs):
        if vc_room.plugin != self:
            return
        return render_plugin_template('room_labels.html', vc_room=vc_room)

    def _times_changed(self, sender, obj, **kwargs):
        from indico.modules.events.models.events import Event
        from indico.modules.events.contributions.models.contributions import Contribution
        from indico.modules.events.sessions.models.blocks import SessionBlock

        if not hasattr(obj, 'vc_room_associations'):
            return

        if any(assoc.vc_room.type == 'zoom' and len(assoc.vc_room.events) == 1 for assoc in obj.vc_room_associations):
            if sender == Event:
                message = _("There are one or more scheduled Zoom meetings associated with this event which were not "
                            "automatically updated.")
            elif sender == Contribution:
                message = _("There are one or more scheduled Zoom meetings associated with contribution '{}' which "
                            " were not automatically updated.").format(obj.title)
            elif sender == SessionBlock:
                message = _("There are one or more scheduled Zoom meetings associated with this session block which "
                            "were not automatically updated.")
            else:
                return

            flash(message, 'warning')