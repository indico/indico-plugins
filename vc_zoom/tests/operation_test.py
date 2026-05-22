# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


TZ = ZoneInfo('Europe/Zurich')


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

    zoom_api['update_meeting'].assert_called_with('zmeeting1', {
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
        return_value=(_aligned_meeting('zmeeting1', approval_type=current_approval_type), is_webinar),
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
        api_mock.assert_called_with('zmeeting1', expected)


@pytest.mark.parametrize('meeting_type', ('regular', 'webinar'))
def test_update_data_vc_room_pushes_approval_type_before_sync(
    create_event, create_zoom_meeting, zoom_plugin, zoom_api, meeting_type,
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
    vc_room.data['auto_register'] = False

    is_webinar = meeting_type == 'webinar'
    api_mock = zoom_api['update_webinar' if is_webinar else 'update_meeting']
    other_mock = zoom_api['update_meeting' if is_webinar else 'update_webinar']
    api_mock.reset_mock()
    other_mock.reset_mock()

    zoom_plugin.update_data_vc_room(vc_room, {'auto_register': True})

    api_mock.assert_called_once_with('zmeeting1', {'settings': {'approval_type': 0}})
    other_mock.assert_not_called()
