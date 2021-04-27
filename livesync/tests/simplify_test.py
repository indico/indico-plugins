# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest

from indico.testing.util import bool_matrix

from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.simplify import CREATED_DELETED, SimpleChange, process_records


class Dummy:
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
    """Test if categories are only kept for certain changes."""
    cascade = mocker.patch('indico_livesync.simplify._process_cascaded_category_contents')
    cascade.return_value = [object()]
    records = [LiveSyncQueueEntry(change=change, type=EntryType.category)]
    if invalid:
        with pytest.raises(AssertionError):
            process_records(records)
    else:
        result = process_records(records)
        assert len(result) == 1
        assert list(result.values())[0] == SimpleChange.updated


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
        # created+deleted items are discarded
        if expected[i] & CREATED_DELETED == CREATED_DELETED:
            expected[i] = 0

    db.session.flush()

    result = process_records(queue)
    assert result == process_records(reversed(queue))  # queue order shouldn't matter
    assert len(result) == sum(1 for x in expected if x)

    result_refs = {obj.id: change for obj, change in result.items()}
    for i, ref in enumerate(refs):
        assert (ref['event_id'] in list(result_refs)) == bool(expected[i])
        assert result_refs.get(ref['event_id'], 0) == expected[i]
