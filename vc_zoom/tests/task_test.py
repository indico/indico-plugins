# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

import pytest
from requests.exceptions import HTTPError

from indico.core.db.sqlalchemy.util.session import no_autoflush
from indico.modules.logs import EventLogRealm, LogKind
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomLinkType, VCRoomStatus
from indico.util.date_time import now_utc

from indico_vc_zoom.util import ZoomMeetingType


@pytest.fixture
def zoom_client(mocker):
    client = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient', autospec=True)
    client.return_value = client
    return client


@pytest.fixture
@no_autoflush
def dummy_vc_room(db, dummy_event, dummy_user):
    zoom_data = {'zoom_id': 0, 'meeting_type': ZoomMeetingType.scheduled_meeting}
    room = VCRoom(type='zoom', name='test', status=VCRoomStatus.created, created_by_user=dummy_user, data=zoom_data)
    room_association = VCRoomEventAssociation(vc_room=room, link_type=VCRoomLinkType.event, data=zoom_data)
    dummy_event.vc_room_associations = [room_association]
    db.session.flush()
    return room


@pytest.mark.usefixtures('dummy_vc_room')
def test_meeting_reschedule(dummy_event, zoom_client):
    from indico_vc_zoom.task import refresh_meetings
    meeting_time = now_utc() - timedelta(days=30)
    log_entry = dummy_event.log(EventLogRealm.event, LogKind.change, 'Test', 'Test', data={'State': 'pending'})
    dummy_event.start_dt = meeting_time + timedelta(days=5)
    refresh_meetings([room.vc_room for room in dummy_event.vc_room_associations], dummy_event, log_entry)
    assert zoom_client.update_meeting.call_count == 1
    assert log_entry.data['State'] == 'succeeded'
    zoom_client.update_meeting.side_effect = HTTPError()
    with pytest.raises(HTTPError):
        refresh_meetings([room.vc_room for room in dummy_event.vc_room_associations], dummy_event, log_entry)
    assert zoom_client.update_meeting.call_count == 2
    assert log_entry.data['State'] == 'failed'


@pytest.mark.usefixtures('db')
def test_refresh_account_directory(zoom_plugin, zoom_api, zoom_directory_cache):
    from indico_vc_zoom.task import refresh_account_directory
    from indico_vc_zoom.util import ZOOM_DIRECTORY_CACHE_KEY
    zoom_plugin.settings.set('allow_auto_register', True)
    zoom_api['list_users'].reset_mock()

    refresh_account_directory()

    assert zoom_api['list_users'].called
    assert zoom_directory_cache.get(ZOOM_DIRECTORY_CACHE_KEY) == {'don.orange@megacorp.xyz'}


@pytest.mark.usefixtures('db', 'zoom_directory_cache')
def test_refresh_account_directory_skipped_without_auto_register(zoom_plugin, zoom_api):
    from indico_vc_zoom.task import refresh_account_directory
    zoom_plugin.settings.set('allow_auto_register', False)
    zoom_api['list_users'].reset_mock()

    refresh_account_directory()

    zoom_api['list_users'].assert_not_called()
