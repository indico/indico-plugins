import pytest
from datetime import datetime, timedelta

from indico.core.db.sqlalchemy.util.session import no_autoflush
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus, VCRoomLinkType
from vc_zoom.indico_vc_zoom.util import ZoomMeetingType


@pytest.fixture
def zoom_client(mocker):
    client = mocker.patch('vc_zoom.indico_vc_zoom.api.ZoomIndicoClient', autospec=True)
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


def test_meeting_reschedule(app, db, dummy_event, dummy_user, dummy_vc_room, zoom_client):
    from vc_zoom.indico_vc_zoom.task import refresh_meetings
    meeting_time = datetime.now() - timedelta(days=30)
    zoom_client.get_meeting.return_value = {
        'id': dummy_vc_room.id,
        'start_time': meeting_time.replace(microsecond=0).isoformat() + 'Z',
        'timezone': 'Europe/Lisbon'
    }
    dummy_event.start_dt = meeting_time + timedelta(days=5)
    refresh_meetings(dummy_event.vc_room_associations, dummy_event.start_dt)
    assert zoom_client.get_meeting.call_count == 1
    assert zoom_client.update_meeting.call_count == 0
    dummy_event.start_dt = dummy_event.start_dt + timedelta(days=26)
    refresh_meetings(dummy_event.vc_room_associations, dummy_event.start_dt)
    assert zoom_client.get_meeting.call_count == 2
    assert zoom_client.update_meeting.call_count == 1
