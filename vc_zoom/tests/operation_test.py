# This file is part of the Indico plugins.
# Copyright (C) 2020 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest

from indico.core.plugins import plugin_engine
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomLinkType, VCRoomStatus

from indico_vc_zoom.plugin import ZoomPlugin


@pytest.fixture
def zoom_plugin(app):
    """Return a callable which lets you create dummy Zoom room occurrences."""
    plugin = ZoomPlugin(plugin_engine, app)
    plugin.settings.set('email_domains', 'megacorp.xyz')
    plugin.settings.set('assistant_id', 'zoom.master@megacorp.xyz')
    return plugin


@pytest.fixture
def create_meeting(create_user, dummy_event, db, zoom_plugin):
    def _create_meeting(name='New Room'):
        user_joe = create_user(1, email='don.orange@megacorp.xyz')

        vc_room = VCRoom(
            type='zoom',
            status=VCRoomStatus.created,
            name=name,
            created_by_id=0,
            data={
                'description': 'something something',
                'password': '1234',
                'host': user_joe.identifier,
                'meeting_type': 'meeting',
                'mute_host_video': False,
                'mute_audio': False,
                'mute_participant_video': False,
                'waiting_room': False
            }
        )
        VCRoomEventAssociation(linked_event=dummy_event, vc_room=vc_room, link_type=VCRoomLinkType.event, data={})
        db.session.flush()
        zoom_plugin.create_room(vc_room, dummy_event)
        return vc_room
    return _create_meeting


@pytest.fixture
def zoom_api(create_user, mocker):
    """Mock some Zoom API endpoints."""
    api_create_meeting = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.create_meeting')
    api_create_meeting.return_value = {
        'id': '12345abc',
        'join_url': 'https://example.com/kitties',
        'start_url': 'https://example.com/puppies',
        'password': '1234',
        'host_id': 'don.orange@megacorp.xyz',
        'topic': 'New Room',
        'agenda': 'something something',
        'settings': {
            'host_video': True,
            'mute_upon_entry': False,
            'participant_video': True,
            'waiting_room': False
        }
    }

    api_update_meeting = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.update_meeting')
    api_update_meeting.return_value = {}

    create_user(1, email='don.orange@megacorp.xyz')

    api_get_user = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_user')
    api_get_user.return_value = {
        'id': '7890abcd',
        'email': 'don.orange@megacorp.xyz'
    }

    api_get_meeting = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting')
    api_get_meeting.return_value = api_create_meeting.return_value

    api_get_assistants = mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_assistants_for_user')
    api_get_assistants.return_value = {
        'assistants': [{'email': 'zoom.master@megacorp.xyz'}]
    }

    return {
        'create_meeting': api_create_meeting,
        'get_meeting': api_get_meeting,
        'update_meeting': api_update_meeting,
        'get_user': api_get_user,
        'get_assistants': api_get_assistants
    }


def test_room_creation(create_meeting, zoom_api):
    vc_room = create_meeting()
    assert vc_room.data['url'] == 'https://example.com/kitties'
    assert vc_room.data['host'] == 'User:1'
    assert zoom_api['create_meeting'].called
    assert zoom_api['get_assistants'].called


def test_host_change(create_user, mocker, create_meeting, zoom_plugin, zoom_api, request_context):
    notify_new_host = mocker.patch('indico_vc_zoom.plugin.notify_new_host')

    create_user(2, email='joe.bidon@megacorp.xyz')
    vc_room = create_meeting()

    assert vc_room.data['host'] == 'User:1'
    assert not vc_room.data['mute_participant_video']
    assert zoom_api['create_meeting'].called
    assert zoom_api['get_assistants'].called

    vc_room.data['host'] = 'User:2'
    vc_room.data['description'] = 'something else'
    zoom_plugin.update_room(vc_room, vc_room.events[0].event)

    assert notify_new_host.called
    assert zoom_api['update_meeting'].call_args == (('12345abc', {
        'schedule_for': 'joe.bidon@megacorp.xyz',
        'agenda': 'something else'
    }),)


def test_password_change(create_user, mocker, create_meeting, zoom_plugin, zoom_api):
    mocker.patch('indico_vc_zoom.plugin.notify_new_host')

    create_user(2, email='joe.bidon@megacorp.xyz')
    vc_room = create_meeting()
    vc_room.data['password'] = '1337'

    # simulate changes between calls of "GET meeting"
    def _get_meeting(self, meeting_id):
        result = {
            'id': meeting_id,
            'join_url': 'https://example.com/llamas' if _get_meeting.called else 'https://example.com/kitties',
            'start_url': 'https://example.com/puppies',
            'password': '1337' if _get_meeting.called else '1234',
            'host_id': 'don.orange@megacorp.xyz',
            'topic': 'New Room',
            'agenda': 'something something',
            'settings': {
                'host_video': True,
                'mute_upon_entry': False,
                'participant_video': True,
                'waiting_room': False
            }
        }
        _get_meeting.called = True
        return result
    _get_meeting.called = False
    mocker.patch('indico_vc_zoom.plugin.ZoomIndicoClient.get_meeting', _get_meeting)

    zoom_plugin.update_room(vc_room, vc_room.events[0].event)

    zoom_api['update_meeting'].assert_called_with('12345abc', {
        'password': '1337'
    })

    assert vc_room.data['password'] == '1337'
    assert vc_room.data['url'] == 'https://example.com/llamas'
