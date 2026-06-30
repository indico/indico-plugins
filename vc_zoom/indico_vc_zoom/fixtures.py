# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from indico.core.plugins import plugin_engine
from indico.modules.events.registration.models.forms import RegistrationForm
from indico.modules.events.registration.models.items import RegistrationFormItemType, RegistrationFormSection
from indico.modules.events.registration.models.registrations import RegistrationState
from indico.modules.events.registration.util import create_personal_data_fields, create_registration
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus


TZ = ZoneInfo('Europe/Zurich')


@pytest.fixture
def zoom_plugin(app):
    """Return a callable which lets you create dummy Zoom meeting occurrences."""
    from indico_vc_zoom.plugin import ZoomPlugin

    plugin = ZoomPlugin(plugin_engine, app)
    plugin.settings.set_multi({
        'email_domains': ('megacorp.xyz',),
        'user_lookup_mode': 'email_domains',
        'allow_language_interpretation': True,
    })
    return plugin


@pytest.fixture
def zoom_user(zoom_api):
    return zoom_api['user']


@pytest.fixture
def reg_form(create_event, db):
    event = create_event(
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
    )
    regform = RegistrationForm(event=event, title='Test Form', currency='EUR')
    section = RegistrationFormSection(registration_form=regform, title='Personal Data',
                                      type=RegistrationFormItemType.section_pd)
    regform.sections.append(section)
    create_personal_data_fields(regform)
    event.registration_forms.append(regform)
    db.session.flush()
    return regform


@pytest.fixture
def create_zoom_meeting(db, test_client, no_csrf_check, smtp, zoom_api):
    def _create(obj, link_type, zoom_name='Zoom Meeting', **kwargs):
        with test_client.session_transaction() as sess:
            sess.set_session_user(zoom_api['user'])
            # despite no_csrf_check, this is still needed since the form does its own
            sess['_csrf_token'] = 'supersecure'  # noqa: S105

        match link_type:
            case 'event':
                event_id = obj.id
            case 'contribution':
                event_id = obj.event_id
            case 'block':
                event_id = obj.session.event_id

        with db.session.no_autoflush:
            resp = test_client.post(
                f'/event/{event_id}/manage/videoconference/zoom/create',
                data={
                    'vc-csrf_token': 'supersecure',
                    'vc-name': zoom_name,
                    'vc-linking': link_type,
                    'vc-host_choice': 'myself',
                    'vc-password': '13371337',
                    'vc-password_visibility': 'logged_in',
                    'vc-description': 'nothing to add',
                    'vc-show': 'y',
                    'vc-mute_participant_video': 'y',
                    'vc-mute_host_video': 'y',
                    'vc-mute_audio': 'y',
                    f'vc-{link_type}': obj.id,
                },
            )
            assert resp.status_code == 200

        db.session.flush()

        # dirty, but this endpoint still returns an old WTForm's HTML
        if b'data-error' in resp.data:
            print(resp.text)
            assert False  # Form error detected

        return obj.vc_room_associations[0].vc_room

    return _create


JSON_DATA = {
    'join_url': 'https://example.com/kitties',
    'start_url': 'https://example.com/puppies',
    'password': '13371337',
    'host_id': 'don.orange@megacorp.xyz',
    'topic': 'New Room',
    'agenda': 'something something',
    'settings': {
        'host_video': True,
        'mute_upon_entry': False,
        'participant_video': True,
        'waiting_room': False,
        'alternative_hosts': 'foo@example.com',
        'approval_type': 2
    },
}


@pytest.fixture
def zoom_api(zoom_plugin, create_user, mocker):
    """Mock some Zoom API endpoints."""
    meeting_ids = itertools.count(start=100000, step=1)

    def _create_meeting(*args, **kwargs):
        return {**JSON_DATA, 'id': next(meeting_ids)}

    api_create_meeting = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.create_meeting')
    api_create_meeting.side_effect = _create_meeting

    api_update_meeting = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.update_meeting')
    api_update_meeting.return_value = {}

    api_update_webinar = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.update_webinar')
    api_update_webinar.return_value = {}

    user = create_user(1, email='don.orange@megacorp.xyz')

    api_get_user = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.get_user')
    api_get_user.return_value = {'id': '7890abcd', 'email': 'don.orange@megacorp.xyz'}

    api_list_users = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.list_users')
    api_list_users.return_value = {'users': [{'email': user.email}], 'next_page_token': ''}

    def _get_meeting(id_, *args, **kwargs):
        return dict(JSON_DATA, id=id_)

    api_get_meeting = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.get_meeting')
    api_get_meeting.side_effect = _get_meeting

    api_delete_meeting = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.delete_meeting')
    api_delete_meeting.return_value = {}

    return {
        'user': user,
        'create_meeting': api_create_meeting,
        'get_meeting': api_get_meeting,
        'update_meeting': api_update_meeting,
        'update_webinar': api_update_webinar,
        'api_delete_meeting': api_delete_meeting,
        'get_user': api_get_user,
        'list_users': api_list_users,
    }


@pytest.fixture
def create_vc_room_with_assoc(db):
    """Create a Zoom VCRoom + association for an event without going through the HTTP endpoint."""
    def _create(event, zoom_user, *, auto_register=True, auto_checkin=False):
        vc_room = VCRoom(name='Test Meeting', type='zoom', status=VCRoomStatus.created, created_by_user=zoom_user)
        vc_room.data = {
            'zoom_id': 26262600,
            'meeting_type': 'regular',
            'host': 'User:1',
            'auto_register': auto_register,
            'auto_checkin': auto_checkin,
        }
        assoc = VCRoomEventAssociation(link_object=event, vc_room=vc_room, show=True,
                                       data={'password_visibility': 'everyone'})
        db.session.add(vc_room)
        db.session.add(assoc)
        db.session.flush()
        return vc_room, assoc
    return _create


@pytest.fixture
def make_complete_registration(db, zoom_plugin):
    """Create a completed registration while auto_register is off to avoid triggering sync."""
    def _make(reg_form, email, first_name, last_name):
        data = {'email': email, 'first_name': first_name, 'last_name': last_name, 'affiliation': 'MegaCorp'}
        form_data = {(getattr(f, 'html_field_name', None) or f.personal_data_type.name): data[f.personal_data_type.name]
                     for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in data}
        form_data['email'] = email

        prev = zoom_plugin.settings.get('allow_auto_register')
        zoom_plugin.settings.set('allow_auto_register', False)
        registration = create_registration(reg_form, form_data)
        db.session.flush()
        registration.state = RegistrationState.complete
        db.session.flush()
        zoom_plugin.settings.set('allow_auto_register', prev)
        return registration
    return _make


@pytest.fixture
def zoom_api_registrants(zoom_api, mocker):
    zoom_api['add_meeting_registrant'] = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.add_meeting_registrant')
    zoom_api['add_webinar_registrant'] = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.add_webinar_registrant')
    zoom_api['update_meeting_registrants_status'] = mocker.patch(
        'indico_vc_zoom.plugin.ZoomIndicoClient.update_meeting_registrants_status')
    zoom_api['update_webinar_registrants_status'] = mocker.patch(
        'indico_vc_zoom.plugin.ZoomIndicoClient.update_webinar_registrants_status')
    zoom_api['list_meeting_registrants'] = mocker.patch(
        'indico_vc_zoom.plugin.ZoomIndicoClient.list_meeting_registrants')
    zoom_api['list_webinar_registrants'] = mocker.patch(
        'indico_vc_zoom.plugin.ZoomIndicoClient.list_webinar_registrants')
    zoom_api['batch_meeting_registrants'] = mocker.patch(
        'indico_vc_zoom.plugin.ZoomIndicoClient.batch_meeting_registrants')
    zoom_api['batch_webinar_registrants'] = mocker.patch(
        'indico_vc_zoom.plugin.ZoomIndicoClient.batch_webinar_registrants')

    zoom_api['add_meeting_registrant'].return_value = {}
    zoom_api['add_webinar_registrant'].return_value = {}
    zoom_api['list_meeting_registrants'].return_value = {'registrants': [{'id': 'reg123', 'email': 'test@example.com'}]}
    zoom_api['list_webinar_registrants'].return_value = {'registrants': [{'id': 'reg123', 'email': 'test@example.com'}]}

    return zoom_api
