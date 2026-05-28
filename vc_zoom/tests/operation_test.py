# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from indico.modules.vc.exceptions import VCRoomError
from indico.web.forms.base import FormDefaults


TZ = ZoneInfo('Europe/Zurich')


def _make_zoom_form(zoom_plugin, app, event, vc_room=None):
    from indico_vc_zoom.forms import VCRoomForm

    zoom_plugin.settings.set('allow_auto_register', True)
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
        'auto_register': vc_room.data.get('auto_register', False) if vc_room is not None else False,
    })
    with app.test_request_context(), zoom_plugin.plugin_context():
        return VCRoomForm(prefix='vc-', obj=defaults, event=event, vc_room=vc_room)


def _aligned_meeting(meeting_id, *, approval_type):
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
            'alternative_hosts': '',
            'approval_type': approval_type,
        },
    }


def test_room_creation(create_zoom_meeting, zoom_api, create_event):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )
    vc_room = create_zoom_meeting(event, 'event')
    assert vc_room.data['url'] == 'https://example.com/kitties'
    assert vc_room.data['host'] == 'User:1'
    assert zoom_api['create_meeting'].called


def test_password_change(create_user, mocker, create_event, create_zoom_meeting, zoom_plugin, zoom_api):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )

    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['password'] = '12341234'

    # simulate changes between calls of "GET meeting"
    def _get_meeting(self, meeting_id):
        result = {
            'id': meeting_id,
            'join_url': 'https://example.com/llamas' if _get_meeting.called else 'https://example.com/kitties',
            'start_url': 'https://example.com/puppies',
            'password': '12341234' if _get_meeting.called else '13371337',
            'host_id': 'don.orange@megacorp.xyz',
            'topic': 'Zoom Meeting',
            'agenda': 'nothing to add',
            'settings': {
                'host_video': False,
                'mute_upon_entry': True,
                'participant_video': False,
                'waiting_room': False,
                'approval_type': 2,
            }
        }
        _get_meeting.called = True
        return result
    _get_meeting.called = False
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting', _get_meeting)

    zoom_plugin.update_room(vc_room, vc_room.events[0].event)

    zoom_api['update_meeting'].assert_called_with(100000, {
        'password': '12341234',
    })

    assert vc_room.data['password'] == '12341234'
    assert vc_room.data['url'] == 'https://example.com/llamas'


@pytest.mark.parametrize('meeting_type', ('regular', 'webinar'))
@pytest.mark.parametrize(('auto_register_before', 'auto_register_after', 'current_approval_type', 'expected'), (
    (False, True, 2, {'settings': {'approval_type': 0}}),
    (True, False, 0, {'settings': {'approval_type': 2}}),
    (True, True, 0, None),
    (False, False, 2, None),
))
def test_update_room_pushes_approval_type(
    mocker, create_event, create_zoom_meeting, zoom_plugin, zoom_api,
    auto_register_before, auto_register_after, current_approval_type, expected, meeting_type,
):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )

    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['meeting_type'] = meeting_type
    vc_room.data['auto_register'] = auto_register_after

    is_webinar = meeting_type == 'webinar'
    mocker.patch(
        'indico_vc_zoom.plugin.fetch_zoom_meeting',
        return_value=(_aligned_meeting(100000, approval_type=current_approval_type), is_webinar),
    )

    api_mock = zoom_api['update_webinar' if is_webinar else 'update_meeting']
    other_mock = zoom_api['update_meeting' if is_webinar else 'update_webinar']
    api_mock.reset_mock()
    other_mock.reset_mock()

    zoom_plugin.update_room(vc_room, vc_room.events[0].event)

    other_mock.assert_not_called()
    if expected is None:
        api_mock.assert_not_called()
    else:
        api_mock.assert_called_with(100000, expected)


@pytest.mark.parametrize('meeting_type', ('regular', 'webinar'))
@pytest.mark.parametrize(('auto_register_before', 'auto_register_after', 'expected_approval_type'), (
    (False, True, 0),
    (True, False, 2),
))
def test_update_data_vc_room_pushes_approval_type_before_sync(
    mocker, create_event, create_zoom_meeting, zoom_plugin, zoom_api, meeting_type,
    auto_register_before, auto_register_after, expected_approval_type,
):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )

    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['meeting_type'] = meeting_type
    vc_room.data['auto_register'] = auto_register_before

    is_webinar = meeting_type == 'webinar'
    mocker.patch(
        'indico_vc_zoom.plugin.fetch_zoom_meeting',
        return_value=(_aligned_meeting(100000, approval_type=expected_approval_type), is_webinar),
    )
    api_mock = zoom_api['update_webinar' if is_webinar else 'update_meeting']
    other_mock = zoom_api['update_meeting' if is_webinar else 'update_webinar']
    api_mock.reset_mock()
    other_mock.reset_mock()

    zoom_plugin.update_data_vc_room(vc_room, {'auto_register': auto_register_after})

    api_mock.assert_called_once_with(100000, {'settings': {'approval_type': expected_approval_type}})
    other_mock.assert_not_called()


def test_create_room_blocks_past_event_with_auto_register(
    create_event, create_zoom_meeting, zoom_plugin, zoom_api,
):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )

    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['auto_register'] = True
    zoom_api['create_meeting'].reset_mock()

    with pytest.raises(VCRoomError):
        zoom_plugin.create_room(vc_room, event)

    zoom_api['create_meeting'].assert_not_called()


@pytest.mark.parametrize('is_webinar', (False, True))
def test_push_approval_type_warns_when_zoom_drops_patch(
    mocker, create_event, create_zoom_meeting, zoom_plugin, zoom_api, is_webinar,
):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )

    vc_room = create_zoom_meeting(event, 'event')

    # Zoom accepts the PATCH (no error) but the read-back shows the value was not honored
    mocker.patch(
        'indico_vc_zoom.plugin.fetch_zoom_meeting',
        return_value=(_aligned_meeting(100000, approval_type=2), is_webinar),
    )
    warning_mock = mocker.patch.object(zoom_plugin.logger, 'warning')

    result = zoom_plugin._push_approval_type(vc_room, 0, is_webinar=is_webinar)

    assert result is False
    warning_mock.assert_called_once()
    assert 'did not honor approval_type' in warning_mock.call_args.args[0]


def test_update_room_warns_when_zoom_drops_approval_type_patch(
    mocker, create_event, create_zoom_meeting, zoom_plugin, zoom_api,
):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event #1',
        creator_has_privileges=True,
    )

    vc_room = create_zoom_meeting(event, 'event')
    vc_room.data['auto_register'] = True

    # Both the pre- and post-PATCH fetches return approval_type=2 (Zoom dropped the change)
    mocker.patch(
        'indico_vc_zoom.plugin.fetch_zoom_meeting',
        return_value=(_aligned_meeting(100000, approval_type=2), False),
    )
    warning_mock = mocker.patch.object(zoom_plugin.logger, 'warning')

    zoom_plugin.update_room(vc_room, vc_room.events[0].event)

    warning_mock.assert_called_once()
    assert 'did not honor approval_type' in warning_mock.call_args.args[0]


def test_auto_register_locked_for_past_event(zoom_plugin, app, create_event, zoom_api):
    past_event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Past event',
        creator_has_privileges=True,
    )

    form = _make_zoom_form(zoom_plugin, app, past_event)

    assert form._auto_register_locked is True
    assert form.auto_register.render_kw == {'disabled': True}
    assert 'cannot be changed' in str(form.auto_register.description)


def test_auto_register_not_locked_for_future_event(zoom_plugin, app, create_event, zoom_api):
    future_event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2099, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2099, 3, 1, 18, 0, tzinfo=TZ),
        title='Future event',
        creator_has_privileges=True,
    )

    form = _make_zoom_form(zoom_plugin, app, future_event)

    assert form._auto_register_locked is False
    assert not (form.auto_register.render_kw or {}).get('disabled')


def test_auto_register_validator_preserves_value_when_locked(
    zoom_plugin, app, create_event, create_zoom_meeting, zoom_api,
):
    past_event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Past event',
        creator_has_privileges=True,
    )
    vc_room = create_zoom_meeting(past_event, 'event')
    vc_room.data['auto_register'] = True  # currently enabled

    form = _make_zoom_form(zoom_plugin, app, past_event, vc_room=vc_room)

    # Simulate a disabled checkbox not being submitted (BooleanField parses to False)
    form.auto_register.data = False
    form.validate_auto_register(form.auto_register)

    assert form.auto_register.data is True
