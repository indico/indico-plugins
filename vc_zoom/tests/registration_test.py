# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from indico.core import signals
from indico.modules.events.registration.models.forms import RegistrationForm
from indico.modules.events.registration.models.items import RegistrationFormItemType, RegistrationFormSection
from indico.modules.events.registration.models.registrations import RegistrationState
from indico.modules.events.registration.util import create_personal_data_fields, create_registration
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus


TZ = ZoneInfo('Europe/Zurich')

@pytest.fixture
def zoom_user(create_user):
    return create_user(1, email='don.orange@megacorp.xyz')


@pytest.fixture
def reg_form(create_event, db):
    event = create_event(
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
    )
    regform = RegistrationForm(event=event, title='Test Form', currency='EUR')
    # Add personal data section
    section = RegistrationFormSection(registration_form=regform, title='Personal Data',
                                      type=RegistrationFormItemType.section_pd)
    regform.sections.append(section)
    create_personal_data_fields(regform)
    event.registration_forms.append(regform)
    db.session.flush()
    return regform


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

    zoom_api['list_meeting_registrants'].return_value = {'registrants': [{'id': 'reg123', 'email': 'test@example.com'}]}
    zoom_api['list_webinar_registrants'].return_value = {'registrants': [{'id': 'reg123', 'email': 'test@example.com'}]}

    return zoom_api


def test_registration_sync_meeting(db, zoom_plugin, zoom_api_registrants, reg_form, create_zoom_meeting, test_client,
                                   zoom_user):
    zoom_plugin.settings.set('auto_register', True)
    event = reg_form.event
    event.update_principal(zoom_user, full_access=True)
    db.session.flush()

    with test_client.session_transaction() as sess:
        sess.set_session_user(zoom_user)
    create_zoom_meeting(event, 'event')

    # Create registration
    data = {
        'email': 'test@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'affiliation': 'MegaCorp'
    }
    # Map the data to form field IDs as expected by create_registration
    form_data = {f.html_field_name: data[f.personal_data_type.name]
                 for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in data}
    form_data['email'] = data['email']

    # We need to set state to complete during creation for the plugin to sync
    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()
    registration.state = RegistrationState.complete
    db.session.flush()

    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()
    zoom_plugin._sync_registration(registration)

    assert zoom_api_registrants['add_meeting_registrant'].called
    # We might have multiple calls, check if John Doe was registered
    assert any(args[1]['email'] == 'test@example.com' and args[1]['first_name'] == 'John'
               for args, _kwargs in zoom_api_registrants['add_meeting_registrant'].call_args_list)

    # Delete registration
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()
    signals.event.registration_deleted.send(registration)

    assert zoom_api_registrants['update_meeting_registrants_status'].called
    assert any(args[1]['action'] == 'cancel' and args[1]['registrants'][0]['email'] == 'test@example.com'
               for args, _kwargs in zoom_api_registrants['update_meeting_registrants_status'].call_args_list)


def test_registration_sync_disabled(db, zoom_plugin, zoom_api_registrants, reg_form, create_zoom_meeting, test_client,
                                    zoom_user):
    zoom_plugin.settings.set('auto_register', False)
    event = reg_form.event
    event.update_principal(zoom_user, full_access=True)
    db.session.flush()

    with test_client.session_transaction() as sess:
        sess.set_session_user(zoom_user)
    create_zoom_meeting(event, 'event')

    data = {'email': 'test@example.com', 'first_name': 'John', 'last_name': 'Doe', 'affiliation': 'MegaCorp'}
    form_data = {f.html_field_name: data[f.personal_data_type.name]
                 for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in data}
    form_data['email'] = data['email']
    # Create registration with sync disabled to avoid triggers during creation
    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()
    registration.state = RegistrationState.complete

    signals.event.registration_created.send(registration)

    zoom_api_registrants['add_meeting_registrant'].assert_not_called()


def test_registration_sync_webinar(db, zoom_plugin, zoom_api_registrants, reg_form, create_zoom_meeting, mocker,
                                   zoom_user):
    zoom_plugin.settings.set('auto_register', True)
    zoom_plugin.settings.set('allow_webinars', True)
    event = reg_form.event

    # Mock create_webinar to return a webinar object
    mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.create_webinar',
                 return_value={
                     'id': 'zwebinar1',
                     'join_url': 'https://example.com/w',
                     'start_url': 'https://example.com/ws',
                     'password': 'pass',
                     'settings': {'approval_type': 0, 'host_video': True}
                 })

    vc_room = VCRoom(name='Webinar', type='zoom', status=VCRoomStatus.created, created_by_user=zoom_user)
    vc_room.data = {
        'zoom_id': 'zwebinar1',
        'meeting_type': 'webinar',
        'host': 'User:1'  # Should match zoom_api user
    }
    assoc = VCRoomEventAssociation(link_object=event, vc_room=vc_room, show=True,
                                   data={'password_visibility': 'everyone'})
    db.session.add(vc_room)
    db.session.add(assoc)
    db.session.flush()

    data = {'email': 'test@example.com', 'first_name': 'John', 'last_name': 'Doe', 'affiliation': 'MegaCorp'}
    form_data = {f.html_field_name: data[f.personal_data_type.name]
                 for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in data}
    form_data['email'] = data['email']

    # We need to set state to complete during creation for the plugin to sync
    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()
    registration.state = RegistrationState.complete
    db.session.flush()

    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['add_webinar_registrant'].reset_mock()
    zoom_plugin._sync_registration(registration)

    assert zoom_api_registrants['add_webinar_registrant'].called
    assert any(args[1]['email'] == 'test@example.com' and args[1]['first_name'] == 'John'
               for args, _kwargs in zoom_api_registrants['add_webinar_registrant'].call_args_list)
