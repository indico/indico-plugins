# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime
from zoneinfo import ZoneInfo
import json
from indico_vc_zoom.fixtures import JSON_DATA

TZ = ZoneInfo('Europe/Zurich')

def test_interpretation_split_join(db, test_client, zoom_api, create_event, smtp, app, mocker):
    event = create_event(
        creator=zoom_api['user'],
        start_dt=datetime(2024, 3, 1, 16, 0, tzinfo=TZ),
        end_dt=datetime(2024, 3, 1, 18, 0, tzinfo=TZ),
        title='Test Event Interpretation',
        creator_has_privileges=True,
    )

    with test_client.session_transaction() as sess:
        sess.set_session_user(zoom_api['user'])
        sess['_csrf_token'] = 'supersecure'

    interpreters = [
        {'email': 'int1@example.com', 'src_lang': 'English', 'target_lang': 'French'},
        {'email': 'int2@example.com', 'src_lang': 'German', 'target_lang': 'Spanish'},
        {'email': 'int3@example.com', 'src_lang': 'English', 'target_lang': 'Korean'},
        {'email': 'int4@example.com', 'src_lang': 'Japanese', 'target_lang': 'Chinese'},
        {'email': 'int5@example.com', 'src_lang': 'Portuguese', 'target_lang': 'Russian'}
    ]

    resp = test_client.post(
        f'/event/{event.id}/manage/videoconference/zoom/create',
        data={
            'vc-csrf_token': 'supersecure',
            'vc-name': 'Interpretation Meeting',
            'vc-linking': 'event',
            'vc-host_choice': 'myself',
            'vc-password': '12345678',
            'vc-password_visibility': 'logged_in',
            'vc-description': 'Testing interpretation',
            'vc-show': 'y',
            'vc-language_interpretation': 'y',
            'vc-interpreters': json.dumps(interpreters),
            'vc-event': event.id,
        },
    )
    assert resp.status_code == 200
    assert b'data-error' not in resp.data

    # Check what was sent to Zoom API
    assert zoom_api['create_meeting'].called
    args, kwargs = zoom_api['create_meeting'].call_args
    sent_settings = kwargs['settings']
    assert sent_settings['language_interpretation']['enable'] is True
    assert sent_settings['language_interpretation']['interpreters'] == [
        {'email': i['email'], 'interpreter_languages': f"{i['src_lang']},{i['target_lang']}"}
        for i in interpreters
    ]

    vc_room = event.vc_room_associations[0].vc_room
    assert vc_room.data['language_interpretation'] is True
    assert len(vc_room.data['interpreters']) == 5
    assert vc_room.data['interpreters'] == interpreters

    # Test Refreshing from Zoom
    # Mock zoom response for refresh
    mocker.patch('indico_vc_zoom.plugin.fetch_zoom_meeting', return_value=({
        **JSON_DATA,
        'id': vc_room.data['zoom_id'],
        'settings': {
            **JSON_DATA['settings'],
            'language_interpretation': {
                'enable': True,
                'interpreters': [
                    {'email': 'int3@example.com', 'interpreter_languages': 'German,Korean'}
                ]
            }
        }
    }, False))

    from indico_vc_zoom.plugin import ZoomPlugin
    from indico.core.plugins import plugin_engine
    plugin = ZoomPlugin(plugin_engine, app)
    plugin.refresh_room(vc_room, event)

    assert vc_room.data['interpreters'] == [
        {'email': 'int3@example.com', 'src_lang': 'German', 'target_lang': 'Korean'}
    ]
