# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2026 CERN
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


@pytest.mark.parametrize(('change', 'invalid', 'simplified'), (
    (ChangeType.created,            True,  None),
    (ChangeType.deleted,            True,  None),
    (ChangeType.data_changed,       True,  None),
    (ChangeType.location_changed,   True,  None),
    (ChangeType.undeleted,          True,  None),
    (ChangeType.published,          False, SimpleChange.created),
    (ChangeType.unpublished,        False, SimpleChange.deleted),
    (ChangeType.protection_changed, False, SimpleChange.updated),
    (ChangeType.moved,              False, SimpleChange.updated),
))
@pytest.mark.usefixtures('queue_entry_dummy_object')
def test_process_records_category_ignored(dummy_agent, dummy_category, dummy_event, change, invalid, simplified):
    """Test if categories are only kept for certain changes."""
    records = [LiveSyncQueueEntry(agent=dummy_agent, change=change, type=EntryType.category, category=dummy_category)]
    if invalid:
        with pytest.raises(AssertionError):
            process_records(records)
    else:
        result = process_records(records)
        assert result == {dummy_event: simplified}


@pytest.mark.parametrize(('change', 'cascade'), (
    (ChangeType.created,            False),
    (ChangeType.deleted,            False),
    (ChangeType.data_changed,       False),
    (ChangeType.protection_changed, True),
    (ChangeType.moved,              True),
))
@pytest.mark.usefixtures('queue_entry_dummy_object', 'db')
def test_process_records_cascade(mocker, change, cascade):
    """Test if certain changes cascade to child elements"""
    cascade_mock = mocker.patch('indico_livesync.simplify._process_cascaded_category_contents')
    records = [LiveSyncQueueEntry(change=change)]
    process_records(records)
    assert cascade_mock.call_args_list[0] == (({records[0]} if cascade else set(),),)
    assert cascade_mock.call_args_list[1] == ((set(),),)
    assert cascade_mock.call_args_list[2] == ((set(),),)


@pytest.mark.parametrize('changes', bool_matrix('......'))
def test_process_records_simplify(changes, db, create_event, dummy_agent):
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
        elif expected[i] & SimpleChange.deleted:
            expected[i] = SimpleChange.deleted
        elif expected[i] & SimpleChange.created:
            expected[i] = SimpleChange.created
        elif expected[i] & SimpleChange.updated:
            expected[i] = SimpleChange.updated

    db.session.flush()

    result = process_records(queue)
    assert result == process_records(reversed(queue))  # queue order shouldn't matter
    assert len(result) == sum(1 for x in expected if x)

    result_refs = {obj.id: change for obj, change in result.items()}
    for i, ref in enumerate(refs):
        assert (ref['event_id'] in list(result_refs)) == bool(expected[i])
        assert result_refs.get(ref['event_id'], 0) == expected[i]


def test_process_records_simplify_created_deleted_child(db, create_event, create_contribution, dummy_agent):
    """Test if deleted items of newly created events are still cascaded.

    This is needed because when cloning an event, there's just a creation
    record for the event itself, but cascading creates creation records for
    all its child objects (e.g. contributions). Now, when such a contribution
    gets deleted WITHOUT a livesync run in between, we have the event creation
    record and a contribution deletion record. But when cascading the creation,
    usually deleted objects are skipped, so we'd try to delete something from
    the search service that doesn't exist there.
    """
    db.session.add(dummy_agent)
    event = create_event()
    contrib1 = create_contribution(event, 'Test 1')
    contrib2 = create_contribution(event, 'Test 2', is_deleted=True)

    queue = [
        LiveSyncQueueEntry(change=ChangeType.created, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.deleted, agent=dummy_agent, type=EntryType.contribution,
                           contribution=contrib2),
    ]

    db.session.flush()
    result = process_records(queue)
    assert result == {
        event: SimpleChange.created,
        contrib1: SimpleChange.created,
    }


def test_process_records_simplify_created_deleted(db, create_event, dummy_agent):
    db.session.add(dummy_agent)
    event = create_event()

    queue = [
        LiveSyncQueueEntry(change=ChangeType.created, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.data_changed, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.deleted, agent=dummy_agent, type=EntryType.event, event=event),
    ]

    db.session.flush()
    result = process_records(queue)
    # creation + deletion should cancel each other out
    assert result == {}


def test_process_records_simplify_created_deleted_undeleted(db, create_event, dummy_agent):
    db.session.add(dummy_agent)
    event = create_event()

    queue = [
        LiveSyncQueueEntry(change=ChangeType.created, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.data_changed, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.deleted, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.undeleted, agent=dummy_agent, type=EntryType.event, event=event),
    ]

    db.session.flush()
    result = process_records(queue)
    # a restore always results in a creation event, even if the other changes cancelled each other
    assert result == {event: SimpleChange.created}


def test_process_records_simplify_deleted_undeleted(db, create_event, dummy_agent):
    db.session.add(dummy_agent)
    event = create_event()

    queue = [
        LiveSyncQueueEntry(change=ChangeType.deleted, agent=dummy_agent, type=EntryType.event, event=event),
        LiveSyncQueueEntry(change=ChangeType.undeleted, agent=dummy_agent, type=EntryType.event, event=event),
    ]

    db.session.flush()
    result = process_records(queue)
    # this is not ideal (an empty dict would be better here, as being deleted first and THEN being restored),
    # could cancel each other, but there is no good way to do this without losing the more important
    # functionality from the test above unless we take the order of changes into account - and with the
    # cascading logic this is not really possible without cascading each queue entry separately, but doing
    # so would likely result in worse performance.
    # see the comment in `process_records` for details
    assert result == {event: SimpleChange.created}
