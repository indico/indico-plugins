# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from datetime import datetime

import pytest

from indico.modules.fulltextindexes.models.events import IndexedEvent
from indico.modules.vc.models.vc_rooms import VCRoom, VCRoomEventAssociation, VCRoomStatus, VCRoomLinkType
from indico_vc_vidyo.models.vidyo_extensions import VidyoExtension


class DummyEvent(object):
    def __init__(self, id_, title, end_date):
        self.id = id_
        self.title = title
        self.end_date = end_date

    def getEndDate(self):
        return self.end_date

    def getId(self):
        return self.id


@pytest.fixture
def create_dummy_room(db, dummy_avatar):
    """Returns a callable which lets you create dummy Vidyo room occurrences"""
    def _create_room(name, extension, owner, data, **kwargs):
        vc_room = VCRoom(
            name=name,
            data=data,
            type="vidyo",
            status=kwargs.pop('status', VCRoomStatus.created),
            created_by_id=kwargs.pop('created_by_id', dummy_avatar.id),
            **kwargs
        )
        db.session.add(vc_room)
        db.session.flush()
        extension = VidyoExtension(
            vc_room_id=vc_room.id,
            extension=extension,
            owned_by_id=owner.id
        )
        vc_room.vidyo_extension = extension
        return vc_room

    return _create_room


def test_room_cleanup(create_dummy_room, dummy_avatar, freeze_time, db):
    """Test that 'old' Vidyo rooms are correctly detected"""
    freeze_time(datetime(2015, 2, 1))

    for id_, (evt_name, end_date) in enumerate((('Event one', datetime(2012, 1, 1)),
                                                ('Event two', datetime(2013, 1, 1)),
                                                ('Event three', datetime(2014, 1, 1)),
                                                ('Event four', datetime(2015, 1, 1))), start=1):
        idx = IndexedEvent(id=id_, title=evt_name, end_date=end_date, start_date=end_date)
        db.session.add(idx)

    for id_, (vidyo_id, extension, evt_ids) in enumerate(((1234, 5678, (1, 2, 3, 4)),
                                                          (1235, 5679, (1, 2)),
                                                          (1235, 5679, (2,)),
                                                          (1236, 5670, (4,)),
                                                          (1237, 5671, ())), start=1):
        room = create_dummy_room('test_room_{}'.format(id_), extension, dummy_avatar, {
            'vidyo_id': vidyo_id
        })
        for evt_id in evt_ids:
            VCRoomEventAssociation(vc_room=room, event_id=evt_id, link_type=VCRoomLinkType.event)
            db.session.flush()

    from indico_vc_vidyo.task import find_old_vidyo_rooms

    assert {r.id for r in find_old_vidyo_rooms(180)} == {2, 3, 5}
