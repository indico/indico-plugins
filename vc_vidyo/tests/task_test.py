# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import datetime

import pytest
from pytz import utc

from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus

from indico_vc_vidyo.models.vidyo_extensions import VidyoExtension


@pytest.fixture
def create_dummy_room(db, dummy_user):
    """Returns a callable which lets you create dummy Vidyo room occurrences"""
    def _create_room(name, extension, data, **kwargs):
        vc_room = VCRoom(
            name=name,
            data=data,
            type='vidyo',
            status=kwargs.pop('status', VCRoomStatus.created),
            created_by_user=dummy_user,
            **kwargs
        )
        db.session.add(vc_room)
        db.session.flush()
        extension = VidyoExtension(
            vc_room_id=vc_room.id,
            extension=extension,
            owned_by_user=dummy_user
        )
        vc_room.vidyo_extension = extension
        return vc_room

    return _create_room


def test_room_cleanup(create_event, create_dummy_room, freeze_time, db):
    """Test that 'old' Vidyo rooms are correctly detected"""
    freeze_time(datetime(2015, 2, 1))

    events = {}
    for id_, (evt_name, end_date) in enumerate((('Event one', datetime(2012, 1, 1, tzinfo=utc)),
                                                ('Event two', datetime(2013, 1, 1, tzinfo=utc)),
                                                ('Event three', datetime(2014, 1, 1, tzinfo=utc)),
                                                ('Event four', datetime(2015, 1, 1, tzinfo=utc))), start=1):
        events[id_] = create_event(id_, title=evt_name, end_dt=end_date, start_dt=end_date)

    for id_, (vidyo_id, extension, evt_ids) in enumerate(((1234, 5678, (1, 2, 3, 4)),
                                                          (1235, 5679, (1, 2)),
                                                          (1235, 5679, (2,)),
                                                          (1236, 5670, (4,)),
                                                          (1237, 5671, ())), start=1):
        room = create_dummy_room(f'test_room_{id_}', extension, {
            'vidyo_id': vidyo_id
        })
        for evt_id in evt_ids:
            VCRoomEventAssociation(vc_room=room, linked_event=events[evt_id], data={})
            db.session.flush()

    from indico_vc_vidyo.task import find_old_vidyo_rooms

    assert {r.id for r in find_old_vidyo_rooms(180)} == {2, 3, 5}
