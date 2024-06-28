# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2024 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime
from zoneinfo import ZoneInfo


TZ = ZoneInfo('Europe/Zurich')


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
                'waiting_room': False
            }
        }
        _get_meeting.called = True
        return result
    _get_meeting.called = False
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting', _get_meeting)

    zoom_plugin.update_room(vc_room, vc_room.events[0].event)

    zoom_api['update_meeting'].assert_called_with('12345abc', {
        'password': '12341234',
    })

    assert vc_room.data['password'] == '12341234'
    assert vc_room.data['url'] == 'https://example.com/llamas'
