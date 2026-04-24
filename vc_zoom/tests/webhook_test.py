# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import hashlib
import hmac as _hmac
import json
import time as _time

import pytest
from registration_test import _create_vc_room_with_assoc, _make_complete_registration

from indico.core import signals
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus


TOKEN = 'test-webhook-secret'


@pytest.fixture
def webhook_client(test_client, zoom_plugin):
    zoom_plugin.settings.set('webhook_token', TOKEN)

    def _post(payload, *, timestamp=None):
        if timestamp is None:
            timestamp = str(int(_time.time()))
        body = json.dumps(payload).encode()
        sig = _hmac.new(TOKEN.encode(), b'v0:' + timestamp.encode() + b':' + body, hashlib.sha256).hexdigest()
        return test_client.post(
            '/api/plugin/zoom/webhook',
            data=body,
            content_type='application/json',
            headers={
                'x-zm-request-timestamp': timestamp,
                'x-zm-signature': f'v0={sig}',
            },
        )

    return _post


# ── Security tests ────────────────────────────────────────────────────────────

def test_webhook_bad_signature_returns_403(db, test_client, zoom_plugin):
    zoom_plugin.settings.set('webhook_token', TOKEN)
    ts = str(int(_time.time()))
    resp = test_client.post(
        '/api/plugin/zoom/webhook',
        json={'event': 'meeting.updated', 'payload': {'object': {'id': 'z1'}}},
        headers={'x-zm-request-timestamp': ts, 'x-zm-signature': 'v0=badsig'},
    )
    assert resp.status_code == 403


# ── participant_joined check-in tests ─────────────────────────────────────────

@pytest.mark.usefixtures('request_context', 'smtp')
def test_participant_joined_checks_in_registration(db, zoom_plugin, reg_form, zoom_user,
                                                    webhook_client):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event
    vc_room, _assoc = _create_vc_room_with_assoc(db, event, zoom_user, auto_register=True, webhook_checkin=True)

    reg = _make_complete_registration(db, zoom_plugin, reg_form, 'test@megacorp.xyz', 'Test', 'User')
    db.session.flush()

    payload = {
        'event': 'meeting.participant_joined',
        'payload': {
            'object': {
                'id': vc_room.data['zoom_id'],
                'participant': {'email': 'test@megacorp.xyz'},
            }
        },
    }
    resp = webhook_client(payload)
    assert resp.status_code == 200
    db.session.refresh(reg)
    assert reg.checked_in
    assert reg.checked_in_dt is not None


@pytest.mark.usefixtures('request_context', 'smtp')
def test_participant_joined_emits_checkin_signal(db, zoom_plugin, reg_form, zoom_user,
                                                  webhook_client, mocker):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event
    vc_room, _assoc = _create_vc_room_with_assoc(db, event, zoom_user, auto_register=True, webhook_checkin=True)

    reg = _make_complete_registration(db, zoom_plugin, reg_form, 'test@megacorp.xyz', 'Test', 'User')
    db.session.flush()

    received = []
    signals.event.registration_checkin_updated.connect(received.append, weak=False)

    payload = {
        'event': 'meeting.participant_joined',
        'payload': {'object': {'id': vc_room.data['zoom_id'], 'participant': {'email': 'test@megacorp.xyz'}}},
    }
    webhook_client(payload)

    signals.event.registration_checkin_updated.disconnect(received.append)
    assert received == [reg]


@pytest.mark.usefixtures('request_context', 'smtp')
def test_participant_joined_unknown_email_returns_200(db, zoom_plugin, reg_form, zoom_user, webhook_client):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event
    vc_room, _assoc = _create_vc_room_with_assoc(db, event, zoom_user, auto_register=True, webhook_checkin=True)
    db.session.flush()

    payload = {
        'event': 'meeting.participant_joined',
        'payload': {'object': {'id': vc_room.data['zoom_id'], 'participant': {'email': 'nobody@megacorp.xyz'}}},
    }
    resp = webhook_client(payload)
    assert resp.status_code == 200


@pytest.mark.usefixtures('request_context', 'smtp')
def test_participant_joined_skipped_when_auto_register_disabled(db, zoom_plugin, reg_form,
                                                                  zoom_user, webhook_client):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event
    vc_room, _assoc = _create_vc_room_with_assoc(db, event, zoom_user, auto_register=False, webhook_checkin=True)

    reg = _make_complete_registration(db, zoom_plugin, reg_form, 'test@megacorp.xyz', 'Test', 'User')
    db.session.flush()

    payload = {
        'event': 'meeting.participant_joined',
        'payload': {'object': {'id': vc_room.data['zoom_id'], 'participant': {'email': 'test@megacorp.xyz'}}},
    }
    resp = webhook_client(payload)
    assert resp.status_code == 200
    db.session.refresh(reg)
    assert not reg.checked_in


@pytest.mark.usefixtures('request_context', 'smtp')
def test_participant_joined_skipped_when_webhook_checkin_disabled(db, zoom_plugin, reg_form,
                                                                   zoom_user, webhook_client):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event
    vc_room, _assoc = _create_vc_room_with_assoc(db, event, zoom_user, auto_register=True, webhook_checkin=False)

    reg = _make_complete_registration(db, zoom_plugin, reg_form, 'test@megacorp.xyz', 'Test', 'User')
    db.session.flush()

    payload = {
        'event': 'meeting.participant_joined',
        'payload': {'object': {'id': vc_room.data['zoom_id'], 'participant': {'email': 'test@megacorp.xyz'}}},
    }
    resp = webhook_client(payload)
    assert resp.status_code == 200
    db.session.refresh(reg)
    assert not reg.checked_in


@pytest.mark.usefixtures('request_context', 'smtp')
def test_participant_joined_idempotent_when_already_checked_in(db, zoom_plugin, reg_form,
                                                                zoom_user, webhook_client):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event
    vc_room, _assoc = _create_vc_room_with_assoc(db, event, zoom_user, auto_register=True, webhook_checkin=True)

    reg = _make_complete_registration(db, zoom_plugin, reg_form, 'test@megacorp.xyz', 'Test', 'User')
    reg.checked_in = True
    db.session.flush()

    payload = {
        'event': 'meeting.participant_joined',
        'payload': {'object': {'id': vc_room.data['zoom_id'], 'participant': {'email': 'test@megacorp.xyz'}}},
    }
    resp = webhook_client(payload)
    assert resp.status_code == 200
    assert reg.checked_in


@pytest.mark.usefixtures('request_context', 'smtp')
def test_webinar_participant_joined_checks_in_registration(db, zoom_plugin, reg_form,
                                                            zoom_user, webhook_client):
    zoom_plugin.settings.set('allow_auto_register', True)
    event = reg_form.event

    vc_room = VCRoom(name='Test Webinar', type='zoom', status=VCRoomStatus.created, created_by_user=zoom_user)
    vc_room.data = {
        'zoom_id': 'zwebinar_test',
        'meeting_type': 'webinar',
        'host': 'User:1',
        'auto_register': True,
        'webhook_checkin': True,
    }
    assoc = VCRoomEventAssociation(link_object=event, vc_room=vc_room, show=True,
                                   data={'password_visibility': 'everyone'})
    db.session.add(vc_room)
    db.session.add(assoc)

    reg = _make_complete_registration(db, zoom_plugin, reg_form, 'webinar@megacorp.xyz', 'Web', 'User')
    db.session.flush()

    payload = {
        'event': 'webinar.participant_joined',
        'payload': {'object': {'id': 'zwebinar_test', 'participant': {'email': 'webinar@megacorp.xyz'}}},
    }
    resp = webhook_client(payload)
    assert resp.status_code == 200
    db.session.refresh(reg)
    assert reg.checked_in
