# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
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

import pytest

from indico.testing.util import bool_matrix

from indico_livesync import SimpleChange, process_records
from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry


class Dummy(object):
    pass


@pytest.fixture
def queue_entry_dummy_object(monkeypatch):
    monkeypatch.setattr(LiveSyncQueueEntry, 'object', object)


@pytest.mark.parametrize(('change', 'invalid'), (
    (ChangeType.created,            True),
    (ChangeType.deleted,            True),
    (ChangeType.data_changed,       True),
    (ChangeType.protection_changed, False),
    (ChangeType.moved,              False),
))
@pytest.mark.usefixtures('queue_entry_dummy_object')
def test_process_records_category_ignored(mocker, change, invalid):
    """Test if categories are only kepy for certain changes"""
    cascade = mocker.patch('indico_livesync.simplify._process_cascaded_category_contents')
    cascade.return_value = [object()]
    records = [LiveSyncQueueEntry(change=change, type=EntryType.category)]
    if invalid:
        with pytest.raises(AssertionError):
            process_records(records)
    else:
        result = process_records(records)
        assert len(result) == 1
        assert result.values()[0] == SimpleChange.updated


@pytest.mark.parametrize(('change', 'cascade'), (
    (ChangeType.created,            False),
    (ChangeType.deleted,            False),
    (ChangeType.data_changed,       False),
    (ChangeType.protection_changed, True),
    (ChangeType.moved,              True),
))
@pytest.mark.usefixtures('queue_entry_dummy_object')
def test_process_records_cascade(mocker, change, cascade):
    """Test if certain changes cascade to child elements"""
    cascade_mock = mocker.patch('indico_livesync.simplify._process_cascaded_category_contents')
    records = [LiveSyncQueueEntry(change=change)]
    process_records(records)
    assert cascade_mock.call_args == (({records[0]} if cascade else set(),),)


@pytest.mark.parametrize('changes', bool_matrix('......'))
def test_process_records_simplify(changes, mocker, db, create_event, dummy_agent):
    """Test if queue entries for the same object are properly simplified"""
    event1 = create_event(id_=1)
    event2 = create_event(id_=2)

    db.session.add(dummy_agent)
    db.session.add(event1)
    db.session.add(event2)

    refs = (
        {'type': EntryType.event, 'event_id': event1.id},
        {'type': EntryType.event, 'event_id': event2.id}
    )

    queue = []
    changes = changes[:3], changes[3:]
    expected = [0, 0]
    for i, ref in enumerate(refs):
        if changes[i][0]:
            queue.append(LiveSyncQueueEntry(change=ChangeType.created, agent=dummy_agent, **ref))
            expected[i] |= SimpleChange.created
        if changes[i][1]:
            queue += [LiveSyncQueueEntry(change=ChangeType.data_changed, agent=dummy_agent, **ref),
                      LiveSyncQueueEntry(change=ChangeType.data_changed, agent=dummy_agent, **ref)]
            expected[i] |= SimpleChange.updated
        if changes[i][2]:
            queue.append(LiveSyncQueueEntry(change=ChangeType.deleted, agent=dummy_agent, **ref))
            expected[i] |= SimpleChange.deleted

    db.session.flush()

    result = process_records(queue)
    assert result == process_records(reversed(queue))  # queue order shouldn't matter
    assert len(result) == sum(1 for x in expected if x)

    result_refs = {obj.id: change for obj, change in result.viewitems()}
    for i, ref in enumerate(refs):
        assert (ref['event_id'] in list(result_refs)) == bool(expected[i])
        assert result_refs.get(ref['event_id'], 0) == expected[i]
