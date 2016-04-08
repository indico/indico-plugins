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
from indico.testing.util import bool_matrix

import pytest

from indico_livesync import process_records, SimpleChange
from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType, EntryType


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
    cascade = mocker.patch('indico_livesync.simplify._cascade')
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
    cascade_mock = mocker.patch('indico_livesync.simplify._cascade')
    records = [LiveSyncQueueEntry(change=change)]
    process_records(records)
    assert cascade_mock.called == cascade


@pytest.mark.parametrize('changes', bool_matrix('......'))
@pytest.mark.usefixtures('queue_entry_dummy_object')
def test_process_records_simplify(changes):
    """Test if queue entries for the same object are properly simplified"""
    refs = (
        LiveSyncQueueEntry(type=EntryType.event, event_id=1).object_ref,
        LiveSyncQueueEntry(type=EntryType.event, event_id=2).object_ref
    )
    queue = []
    changes = changes[:3], changes[3:]
    expected = [0, 0]
    for i, ref in enumerate(refs):
        if changes[i][0]:
            queue.append(LiveSyncQueueEntry(change=ChangeType.created, **ref))
            expected[i] |= SimpleChange.created
        if changes[i][1]:
            queue.append(LiveSyncQueueEntry(change=ChangeType.data_changed, **ref))
            queue.append(LiveSyncQueueEntry(change=ChangeType.data_changed, **ref))
            expected[i] |= SimpleChange.updated
        if changes[i][2]:
            queue.append(LiveSyncQueueEntry(change=ChangeType.deleted, **ref))
            expected[i] |= SimpleChange.deleted

    result = process_records(queue)
    assert result == process_records(reversed(queue))  # queue order shouldn't matter
    assert len(result) == sum(1 for x in expected if x)
    for i, ref in enumerate(refs):
        assert (ref in result) == bool(expected[i])
        assert result[ref] == expected[i]
