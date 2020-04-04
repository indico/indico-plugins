
from datetime import datetime

import pytest
from pytz import utc

from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus

from indico_vc_zoom.models.zoom_meetings import ZoomMeeting


@pytest.fixture
def create_dummy_room(db, dummy_user):
    """Returns a callable which lets you create dummy Zoom room occurrences"""
    pass


def test_room_cleanup(create_event, create_dummy_room, freeze_time, db):
    """Test that 'old' Zoom rooms are correctly detected"""
    freeze_time(datetime(2015, 2, 1))

    pass

    assert {r.id for r in find_old_zoom_rooms(180)} == {2, 3, 5}
