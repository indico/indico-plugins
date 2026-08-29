# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest

from indico.core import signals
from indico.modules.events.registration.models.registrations import RegistrationState


@pytest.fixture
def two_regforms(reg_form, create_reg_form):
    return reg_form, create_reg_form(reg_form.event, 'Second Form')


@pytest.mark.usefixtures('smtp')
def test_room_creation_syncs_only_selected_regforms(zoom_plugin, zoom_api_registrants, two_regforms, zoom_user,
                                                    create_vc_room_with_assoc, make_complete_registration):
    selected, other = two_regforms
    make_complete_registration(selected, 'alice@example.com', 'Alice', 'Smith')
    make_complete_registration(other, 'bob@example.com', 'Bob', 'Jones')

    zoom_plugin.settings.set('allow_auto_register', True)
    zoom_api_registrants['add_meeting_registrant'].reset_mock()

    vc_room, assoc = create_vc_room_with_assoc(selected.event, zoom_user, registration_forms=[selected.id])
    signals.vc.vc_room_created.send(vc_room, event=selected.event, assoc=assoc)
    zoom_plugin._flush_pending_registrations(None)

    zoom_api_registrants['batch_meeting_registrants'].assert_not_called()
    assert zoom_api_registrants['add_meeting_registrant'].call_count == 1
    assert zoom_api_registrants['add_meeting_registrant'].call_args[0][1]['email'] == 'alice@example.com'


@pytest.mark.usefixtures('smtp')
def test_room_creation_syncs_every_regform_when_unset(zoom_plugin, zoom_api_registrants, two_regforms, zoom_user,
                                                      create_vc_room_with_assoc, make_complete_registration):
    first, second = two_regforms
    make_complete_registration(first, 'alice@example.com', 'Alice', 'Smith')
    make_complete_registration(second, 'bob@example.com', 'Bob', 'Jones')

    zoom_plugin.settings.set('allow_auto_register', True)
    zoom_api_registrants['batch_meeting_registrants'].reset_mock()

    vc_room, assoc = create_vc_room_with_assoc(first.event, zoom_user, registration_forms=None)
    signals.vc.vc_room_created.send(vc_room, event=first.event, assoc=assoc)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['batch_meeting_registrants'].call_count == 1
    batch_data = zoom_api_registrants['batch_meeting_registrants'].call_args[0][1]
    assert {r['email'] for r in batch_data['registrants']} == {'alice@example.com', 'bob@example.com'}


@pytest.mark.usefixtures('request_context', 'smtp')
def test_removal_ignores_registration_in_unselected_regform(db, zoom_plugin, zoom_api_registrants, two_regforms,
                                                            zoom_user, create_vc_room_with_assoc,
                                                            make_complete_registration):
    """A registration in an unselected form must not keep someone in the Zoom meeting."""
    selected, other = two_regforms
    registration = make_complete_registration(selected, 'shared@example.com', 'Shared', 'User')
    make_complete_registration(other, 'shared@example.com', 'Shared', 'User')

    zoom_plugin.settings.set('allow_auto_register', True)
    create_vc_room_with_assoc(selected.event, zoom_user, registration_forms=[selected.id])
    zoom_api_registrants['list_meeting_registrants'].return_value = {
        'registrants': [{'id': 'reg_shared', 'email': 'shared@example.com'}]
    }
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()

    registration.state = RegistrationState.withdrawn
    db.session.flush()
    signals.event.registration_state_updated.send(registration, previous_state=RegistrationState.complete)
    zoom_plugin._flush_pending_registrations(None)

    status_data = zoom_api_registrants['update_meeting_registrants_status'].call_args[0][1]
    assert status_data['action'] == 'cancel'
    assert {r['email'] for r in status_data['registrants']} == {'shared@example.com'}


@pytest.mark.usefixtures('request_context', 'smtp')
def test_selection_change_adds_and_removes_registrants(zoom_plugin, zoom_api_registrants, two_regforms, zoom_user,
                                                       create_vc_room_with_assoc, make_complete_registration):
    dropped, added = two_regforms
    make_complete_registration(dropped, 'alice@example.com', 'Alice', 'Smith')
    make_complete_registration(added, 'bob@example.com', 'Bob', 'Jones')

    zoom_plugin.settings.set('allow_auto_register', True)
    vc_room, _assoc = create_vc_room_with_assoc(dropped.event, zoom_user, registration_forms=[dropped.id])
    zoom_api_registrants['list_meeting_registrants'].return_value = {
        'registrants': [{'id': 'reg_alice', 'email': 'alice@example.com'}]
    }
    zoom_api_registrants['add_meeting_registrant'].reset_mock()
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()

    zoom_plugin.update_data_vc_room(vc_room, {'registration_forms': [added.id]}, is_new=False)
    zoom_plugin._flush_pending_registrations(None)

    assert zoom_api_registrants['add_meeting_registrant'].call_count == 1
    assert zoom_api_registrants['add_meeting_registrant'].call_args[0][1]['email'] == 'bob@example.com'
    status_data = zoom_api_registrants['update_meeting_registrants_status'].call_args[0][1]
    assert {r['email'] for r in status_data['registrants']} == {'alice@example.com'}


@pytest.mark.usefixtures('request_context', 'smtp')
def test_selection_change_keeps_registrant_of_still_selected_regform(zoom_plugin, zoom_api_registrants, two_regforms,
                                                                     zoom_user, create_vc_room_with_assoc,
                                                                     make_complete_registration):
    dropped, kept = two_regforms
    make_complete_registration(dropped, 'shared@example.com', 'Shared', 'User')
    make_complete_registration(kept, 'shared@example.com', 'Shared', 'User')

    zoom_plugin.settings.set('allow_auto_register', True)
    vc_room, _assoc = create_vc_room_with_assoc(dropped.event, zoom_user,
                                                registration_forms=[dropped.id, kept.id])
    zoom_api_registrants['list_meeting_registrants'].return_value = {
        'registrants': [{'id': 'reg_shared', 'email': 'shared@example.com'}]
    }
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()

    zoom_plugin.update_data_vc_room(vc_room, {'registration_forms': [kept.id]}, is_new=False)
    zoom_plugin._flush_pending_registrations(None)

    zoom_api_registrants['update_meeting_registrants_status'].assert_not_called()


@pytest.mark.usefixtures('db', 'smtp')
def test_personalized_join_url_only_for_selected_regform(zoom_plugin, zoom_api_registrants, two_regforms, zoom_user,
                                                         create_user, create_vc_room_with_assoc,
                                                         make_complete_registration):
    selected, other = two_regforms
    participant = create_user(2, email='jane.doe@megacorp.xyz')
    make_complete_registration(other, participant.email, 'Jane', 'Doe')

    zoom_plugin.settings.set('allow_auto_register', True)
    vc_room, assoc = create_vc_room_with_assoc(selected.event, zoom_user, registration_forms=[selected.id])

    assert zoom_plugin.get_personalized_join_url(vc_room, assoc, participant) is None
    zoom_api_registrants['list_meeting_registrants'].assert_not_called()


@pytest.mark.usefixtures('request_context', 'db', 'smtp')
def test_registration_summary_hides_link_for_unselected_regform(zoom_plugin, zoom_api_registrants, two_regforms,
                                                                zoom_user, create_vc_room_with_assoc,
                                                                make_complete_registration):
    selected, other = two_regforms
    registration = make_complete_registration(other, 'test@example.com', 'John', 'Doe')

    zoom_plugin.settings.set('allow_auto_register', True)
    create_vc_room_with_assoc(selected.event, zoom_user, registration_forms=[selected.id])

    assert zoom_plugin._render_registration_zoom_link(registration, from_management=False) == ''
    zoom_api_registrants['list_meeting_registrants'].assert_not_called()


@pytest.mark.usefixtures('smtp')
@pytest.mark.parametrize('restrict_to_form', (True, False))
def test_deleted_regform_removes_its_registrants(db, zoom_plugin, zoom_api_registrants, two_regforms, zoom_user,
                                                 create_vc_room_with_assoc, make_complete_registration,
                                                 restrict_to_form):
    """Registrants of a deleted form leave the meeting even though the form is gone."""
    deleted, other = two_regforms
    make_complete_registration(deleted, 'alice@example.com', 'Alice', 'Smith')
    make_complete_registration(other, 'bob@example.com', 'Bob', 'Jones')

    zoom_plugin.settings.set('allow_auto_register', True)
    create_vc_room_with_assoc(deleted.event, zoom_user,
                              registration_forms=[deleted.id] if restrict_to_form else None)
    zoom_api_registrants['list_meeting_registrants'].return_value = {
        'registrants': [{'id': 'reg_alice', 'email': 'alice@example.com'}]
    }
    zoom_api_registrants['update_meeting_registrants_status'].reset_mock()

    deleted.is_deleted = True
    db.session.flush()
    signals.event.registration_form_deleted.send(deleted)
    zoom_plugin._flush_pending_registrations(None)

    status_data = zoom_api_registrants['update_meeting_registrants_status'].call_args[0][1]
    assert {r['email'] for r in status_data['registrants']} == {'alice@example.com'}
