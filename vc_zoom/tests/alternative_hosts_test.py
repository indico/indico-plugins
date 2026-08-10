# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import json
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from flask import session

from indico.web.forms.base import FormDefaults


TZ = ZoneInfo('Europe/Zurich')


@pytest.fixture
def alt_host(create_user):
    return create_user(2, email='ada.lovelace@megacorp.xyz')


@pytest.fixture
def event(create_event, zoom_api):
    return create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )


@contextmanager
def _make_form(zoom_plugin, app, event, vc_room=None, formdata=None, user=None):
    from indico_vc_zoom.forms import VCRoomForm

    defaults = FormDefaults({
        'name': 'Test',
        'password': '12345678',
        'host_choice': 'myself',
        'description': '',
        'meeting_type': 'regular',
        'linking': 'event',
        'mute_audio': True,
        'mute_host_video': True,
        'mute_participant_video': True,
        'waiting_room': False,
        'alternative_hosts': vc_room.data['alternative_hosts'] if vc_room is not None else [],
        'host': vc_room.data['host'] if vc_room is not None else None,
    })
    with app.test_request_context(method='POST', data=formdata), zoom_plugin.plugin_context():
        if user is not None:
            session.set_session_user(user)
        yield VCRoomForm(prefix='vc-', obj=defaults, event=event, vc_room=vc_room)


def _zoom_meeting(meeting_id, alternative_hosts):
    return {
        'id': meeting_id,
        'join_url': 'https://example.com/kitties',
        'start_url': 'https://example.com/puppies',
        'password': '13371337',
        'host_id': 'don.orange@megacorp.xyz',
        'topic': 'Zoom Meeting',
        'agenda': 'nothing to add',
        'settings': {
            'host_video': False,
            'mute_upon_entry': True,
            'participant_video': False,
            'waiting_room': False,
            'alternative_hosts': alternative_hosts,
            'approval_type': 2,
        },
    }


def _patched_alternative_hosts(api_mock):
    return api_mock.call_args.args[1]['settings']['alternative_hosts']


def test_create_room_sends_alternative_hosts(create_zoom_meeting, zoom_plugin, zoom_api, event, alt_host):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier]
    zoom_api['create_meeting'].reset_mock()

    zoom_plugin.create_room(vc_room, event)

    settings = zoom_api['create_meeting'].call_args.kwargs['settings']
    assert settings['alternative_hosts'] == 'ada.lovelace@megacorp.xyz'


def test_create_room_without_alternative_hosts_omits_setting(create_zoom_meeting, zoom_plugin, zoom_api, event):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = []
    zoom_api['create_meeting'].reset_mock()

    zoom_plugin.create_room(vc_room, event)

    assert 'alternative_hosts' not in zoom_api['create_meeting'].call_args.kwargs['settings']


def test_create_webinar_keeps_host_as_alternative_host(mocker, create_zoom_meeting, zoom_plugin, zoom_api, event,
                                                       alt_host):
    create_webinar = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.create_webinar')
    create_webinar.side_effect = zoom_api['create_meeting'].side_effect
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['meeting_type'] = 'webinar'
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier]

    zoom_plugin.create_room(vc_room, event)

    settings = create_webinar.call_args.kwargs['settings']
    assert settings['alternative_hosts'] == 'don.orange@megacorp.xyz,ada.lovelace@megacorp.xyz'


def test_create_webinar_does_not_store_host_as_alternative_host(mocker, create_zoom_meeting, zoom_plugin, zoom_api,
                                                                event, alt_host):
    create_webinar = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.create_webinar')
    create_webinar.side_effect = lambda user_id, **kwargs: _zoom_meeting(123456,
                                                                        kwargs['settings']['alternative_hosts'])
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['meeting_type'] = 'webinar'
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier]

    zoom_plugin.create_room(vc_room, event)

    assert vc_room.data['alternative_hosts'] == [alt_host.persistent_identifier]


def test_update_room_pushes_alternative_hosts(mocker, create_zoom_meeting, zoom_plugin, zoom_api, event, alt_host):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier]
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting',
                 side_effect=lambda id_, *a, **kw: _zoom_meeting(id_, ''))
    api_mock = mocker.patch('indico_vc_zoom.util.ZoomIndicoClient.update_meeting')

    zoom_plugin.update_room(vc_room, event)

    assert _patched_alternative_hosts(api_mock) == 'ada.lovelace@megacorp.xyz'


def test_update_room_ignores_alternative_host_order(mocker, create_zoom_meeting, zoom_plugin, zoom_api, event,
                                                    alt_host, create_user):
    other = create_user(3, email='alan.turing@megacorp.xyz')
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier, other.persistent_identifier]
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting',
                 side_effect=lambda id_, *a, **kw: _zoom_meeting(
                     id_, 'alan.turing@megacorp.xyz,ada.lovelace@megacorp.xyz'))
    api_mock = mocker.patch('indico_vc_zoom.util.ZoomIndicoClient.update_meeting')

    zoom_plugin.update_room(vc_room, event)

    api_mock.assert_not_called()


def test_update_room_keeps_alternative_hosts_without_indico_user(mocker, create_zoom_meeting, zoom_plugin, zoom_api,
                                                                 event, alt_host):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier]
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting',
                 side_effect=lambda id_, *a, **kw: _zoom_meeting(id_, 'av-team@megacorp.xyz'))
    api_mock = mocker.patch('indico_vc_zoom.util.ZoomIndicoClient.update_meeting')

    zoom_plugin.update_room(vc_room, event)

    assert _patched_alternative_hosts(api_mock) == 'ada.lovelace@megacorp.xyz,av-team@megacorp.xyz'


def test_update_room_does_not_wipe_alternative_host_without_indico_user(mocker, create_zoom_meeting, zoom_plugin,
                                                                        zoom_api, event):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = []
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting',
                 side_effect=lambda id_, *a, **kw: _zoom_meeting(id_, 'av-team@megacorp.xyz'))
    api_mock = mocker.patch('indico_vc_zoom.util.ZoomIndicoClient.update_meeting')

    zoom_plugin.update_room(vc_room, event)

    api_mock.assert_not_called()


def test_form_stores_alternative_hosts_as_identifiers(zoom_plugin, app, event, zoom_api, zoom_user, alt_host):
    formdata = {'vc-alternative_host_users': json.dumps([alt_host.identifier])}

    with _make_form(zoom_plugin, app, event, formdata=formdata, user=zoom_user) as form:
        assert form.data['alternative_hosts'] == [alt_host.persistent_identifier]


def test_form_rejects_alternative_host_without_zoom_account(zoom_plugin, app, no_csrf_check, event, zoom_api,
                                                            zoom_user, create_user):
    outsider = create_user(4, email='grace.hopper@example.com')
    formdata = {'vc-alternative_host_users': json.dumps([outsider.identifier])}

    with _make_form(zoom_plugin, app, event, formdata=formdata, user=zoom_user) as form:
        assert not form.validate()
        assert 'no Zoom account' in str(form.alternative_host_users.errors[0])


def test_form_rejects_host_as_alternative_host(zoom_plugin, app, no_csrf_check, event, zoom_api, zoom_user):
    formdata = {'vc-alternative_host_users': json.dumps([zoom_user.identifier])}

    with _make_form(zoom_plugin, app, event, formdata=formdata, user=zoom_user) as form:
        assert not form.validate()
        assert 'cannot be an alternative host' in str(form.alternative_host_users.errors[0])


def test_form_omits_host_from_alternative_hosts_when_editing(zoom_plugin, app, create_zoom_meeting, event, zoom_api,
                                                             alt_host, zoom_user):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = [zoom_user.persistent_identifier, alt_host.persistent_identifier]

    with _make_form(zoom_plugin, app, event, vc_room=vc_room) as form:
        assert form.alternative_host_users.data == {alt_host}


def test_form_prefills_alternative_hosts_when_editing(zoom_plugin, app, create_zoom_meeting, event, zoom_api,
                                                      alt_host):
    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['alternative_hosts'] = [alt_host.persistent_identifier]

    with _make_form(zoom_plugin, app, event, vc_room=vc_room) as form:
        assert form.alternative_host_users.data == {alt_host}
