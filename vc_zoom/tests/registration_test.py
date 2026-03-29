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
    zoom_plugin._queue_registration_sync(registration, remove=False)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['add_meeting_registrant'].called
    # We might have multiple calls, check if John Doe was registered
    assert any(args[1]['email'] == 'test@example.com' and args[1]['first_name'] == 'John'
               for args, _kwargs in zoom_api_registrants['add_meeting_registrant'].call_args_list)

    # Delete registration
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()
    signals.event.registration_deleted.send(registration)
    zoom_plugin._flush_pending_registrations(None)

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
    zoom_plugin._flush_pending_registrations(None)

    zoom_api_registrants['add_meeting_registrant'].assert_not_called()


def test_registration_state_updated_approve(db, zoom_plugin, zoom_api_registrants, reg_form, create_zoom_meeting,
                                             test_client, zoom_user):
    zoom_plugin.settings.set('auto_register', True)
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

    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()

    # Simulate approving a pending registration
    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()
    registration.state = RegistrationState.complete
    db.session.flush()
    signals.event.registration_state_updated.send(registration, previous_state=RegistrationState.pending)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['add_meeting_registrant'].called


def test_registration_state_updated_withdraw(db, zoom_plugin, zoom_api_registrants, reg_form, create_zoom_meeting,
                                              test_client, zoom_user):
    zoom_plugin.settings.set('auto_register', True)
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

    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()
    registration.state = RegistrationState.complete
    db.session.flush()

    # Simulate withdrawing a registration
    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()
    registration.state = RegistrationState.withdrawn
    db.session.flush()
    signals.event.registration_state_updated.send(registration, previous_state=RegistrationState.complete)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['update_meeting_registrants_status'].called
    assert any(args[1]['action'] == 'cancel'
               for args, _kwargs in zoom_api_registrants['update_meeting_registrants_status'].call_args_list)


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
    zoom_plugin._queue_registration_sync(registration, remove=False)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['add_webinar_registrant'].called
    assert any(args[1]['email'] == 'test@example.com' and args[1]['first_name'] == 'John'
               for args, _kwargs in zoom_api_registrants['add_webinar_registrant'].call_args_list)


def test_registration_form_deleted_batches_removals(db, zoom_plugin, zoom_api_registrants, reg_form,
                                                     create_zoom_meeting, test_client, zoom_user):
    """Deleting a form with multiple registrations should batch API calls (one list + one cancel per meeting)."""
    zoom_plugin.settings.set('auto_register', True)
    event = reg_form.event
    event.update_principal(zoom_user, full_access=True)
    db.session.flush()

    with test_client.session_transaction() as sess:
        sess.set_session_user(zoom_user)
    create_zoom_meeting(event, 'event')

    # Create two registrations with different emails
    zoom_plugin.settings.set('auto_register', False)
    registrations = []
    for email, first, last in [('alice@example.com', 'Alice', 'Smith'), ('bob@example.com', 'Bob', 'Jones')]:
        person = {'email': email, 'first_name': first, 'last_name': last, 'affiliation': 'MegaCorp'}
        form_data = {f.html_field_name: person[f.personal_data_type.name]
                     for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in person}
        form_data['email'] = email
        reg = create_registration(reg_form, form_data)
        db.session.flush()
        reg.state = RegistrationState.complete
        db.session.flush()
        registrations.append(reg)

    # Mock list to return both registrants in one page
    zoom_api_registrants['list_meeting_registrants'].return_value = {
        'registrants': [
            {'id': 'reg_alice', 'email': 'alice@example.com'},
            {'id': 'reg_bob', 'email': 'bob@example.com'},
        ]
    }

    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['list_meeting_registrants'].reset_mock()
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()

    # Delete the registration form: should queue all removals, then batch them on flush
    signals.event.registration_form_deleted.send(reg_form)
    zoom_plugin._flush_pending_registrations(None)

    # Only ONE list call and ONE status update (batched), not two of each
    assert zoom_api_registrants['list_meeting_registrants'].call_count == 1
    assert zoom_api_registrants['update_meeting_registrants_status'].call_count == 1

    # The cancel should include both registrants
    status_data = zoom_api_registrants['update_meeting_registrants_status'].call_args[0][1]
    assert status_data['action'] == 'cancel'
    cancelled_emails = {r['email'] for r in status_data['registrants']}
    assert cancelled_emails == {'alice@example.com', 'bob@example.com'}


def _create_vc_room_with_assoc(db, event, zoom_user):
    """Create a Zoom VCRoom + association for an event without going through the HTTP endpoint."""
    vc_room = VCRoom(name='Test Meeting', type='zoom', status=VCRoomStatus.created, created_by_user=zoom_user)
    vc_room.data = {
        'zoom_id': 'zmeeting_manual',
        'meeting_type': 'regular',
        'host': 'User:1',
    }
    assoc = VCRoomEventAssociation(link_object=event, vc_room=vc_room, show=True,
                                   data={'password_visibility': 'everyone'})
    db.session.add(vc_room)
    db.session.add(assoc)
    db.session.flush()
    return vc_room, assoc


def _make_complete_registration(db, zoom_plugin, reg_form, email, first_name, last_name):
    """Create a completed registration while auto_register is off to avoid triggering sync."""
    data = {'email': email, 'first_name': first_name, 'last_name': last_name, 'affiliation': 'MegaCorp'}
    form_data = {f.html_field_name: data[f.personal_data_type.name]
                 for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in data}
    form_data['email'] = email

    prev = zoom_plugin.settings.get('auto_register')
    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()
    registration.state = RegistrationState.complete
    db.session.flush()
    zoom_plugin.settings.set('auto_register', prev)
    return registration


def test_vc_room_created_syncs_existing_registrations(db, smtp, zoom_plugin, zoom_api_registrants, reg_form, zoom_user):
    """Creating a Zoom meeting should sync pre-existing completed registrations."""
    event = reg_form.event
    _make_complete_registration(db, zoom_plugin, reg_form, 'test@example.com', 'John', 'Doe')

    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()

    vc_room, assoc = _create_vc_room_with_assoc(db, event, zoom_user)
    signals.vc.vc_room_created.send(vc_room, event=event, assoc=assoc)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['add_meeting_registrant'].call_count == 1
    reg_data = zoom_api_registrants['add_meeting_registrant'].call_args[0][1]
    assert reg_data['email'] == 'test@example.com'
    assert reg_data['first_name'] == 'John'


def test_vc_room_created_auto_register_disabled(db, smtp, zoom_plugin, zoom_api_registrants, reg_form, zoom_user):
    """No sync when auto_register is disabled."""
    event = reg_form.event
    _make_complete_registration(db, zoom_plugin, reg_form, 'test@example.com', 'John', 'Doe')

    zoom_plugin.settings.set('auto_register', False)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()

    vc_room, assoc = _create_vc_room_with_assoc(db, event, zoom_user)
    signals.vc.vc_room_created.send(vc_room, event=event, assoc=assoc)
    zoom_plugin._flush_pending_registrations(None)

    zoom_api_registrants['add_meeting_registrant'].assert_not_called()


def test_vc_room_created_skips_non_complete_registrations(db, smtp, zoom_plugin, zoom_api_registrants,
                                                          reg_form, zoom_user):
    """Only completed registrations are synced to Zoom on room creation."""
    event = reg_form.event

    data = {'email': 'pending@example.com', 'first_name': 'Pending', 'last_name': 'User', 'affiliation': 'MegaCorp'}
    form_data = {f.html_field_name: data[f.personal_data_type.name]
                 for f in reg_form.active_fields if f.personal_data_type and f.personal_data_type.name in data}
    form_data['email'] = data['email']

    zoom_plugin.settings.set('auto_register', False)
    registration = create_registration(reg_form, form_data)
    db.session.flush()
    registration.state = RegistrationState.pending
    db.session.flush()

    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()

    vc_room, assoc = _create_vc_room_with_assoc(db, event, zoom_user)
    signals.vc.vc_room_created.send(vc_room, event=event, assoc=assoc)
    zoom_plugin._flush_pending_registrations(None)

    zoom_api_registrants['add_meeting_registrant'].assert_not_called()


def test_collect_room_ops_deduplicates_by_email(db, smtp, zoom_plugin, zoom_api_registrants, reg_form, zoom_user,
                                                 create_event):
    """Two registrations with the same email (from different forms) should produce one Zoom registrant."""
    event = reg_form.event

    # Create a second registration form on the same event
    reg_form_2 = RegistrationForm(event=event, title='Second Form', currency='EUR')
    section = RegistrationFormSection(registration_form=reg_form_2, title='Personal Data',
                                      type=RegistrationFormItemType.section_pd)
    reg_form_2.sections.append(section)
    create_personal_data_fields(reg_form_2)
    event.registration_forms.append(reg_form_2)
    db.session.flush()

    # Register same email in both forms
    reg1 = _make_complete_registration(db, zoom_plugin, reg_form, 'dupe@example.com', 'John', 'Doe')
    reg2 = _make_complete_registration(db, zoom_plugin, reg_form_2, 'dupe@example.com', 'John', 'Doe')
    assert reg1.id != reg2.id

    zoom_plugin.settings.set('auto_register', True)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()

    vc_room, assoc = _create_vc_room_with_assoc(db, event, zoom_user)
    signals.vc.vc_room_created.send(vc_room, event=event, assoc=assoc)
    zoom_plugin._flush_pending_registrations(None)

    # Should only call once despite two registrations with the same email
    assert zoom_api_registrants['add_meeting_registrant'].call_count == 1
    reg_data = zoom_api_registrants['add_meeting_registrant'].call_args[0][1]
    assert reg_data['email'] == 'dupe@example.com'
