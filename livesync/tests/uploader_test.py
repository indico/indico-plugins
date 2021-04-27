# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from unittest.mock import MagicMock, Mock

from indico.modules.events import Event

from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.simplify import SimpleChange
from indico_livesync.uploader import Uploader


class RecordingUploader(Uploader):
    """An uploader which logs each 'upload'"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uploaded = []
        self.logger = MagicMock()

    def upload_records(self, records):
        self._uploaded.append(list(records))

    @property
    def all_uploaded(self):
        return self._uploaded


class FailingUploader(RecordingUploader):
    """An uploader where the second batch fails"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._n = 0

    def upload_records(self, records):
        super().upload_records(records)
        self._n += 1
        if self._n == 2:
            raise Exception('All your data are belong to us!')


def test_run_initial(mocker):
    """Test the initial upload"""
    mocker.patch.object(Uploader, 'processed_records', autospec=True)
    mocker.patch('indico_livesync.uploader.verbose_iterator', new=lambda it, *a, **kw: it)
    uploader = RecordingUploader(MagicMock())
    records = tuple(Mock(spec=Event, id=evt_id) for evt_id in range(4))
    uploader.run_initial(records, 4)
    assert uploader.all_uploaded == [[(record, SimpleChange.created) for record in records]]
    # During an initial export there are no records to mark as processed
    assert not uploader.processed_records.called


def test_run(mocker, db, create_event, dummy_agent):
    """Test uploading queued data"""
    uploader = RecordingUploader(MagicMock())
    uploader.BATCH_SIZE = 3

    events = tuple(create_event(id_=evt_id) for evt_id in range(4))
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event_id=evt.id,
                                       agent=dummy_agent)
                    for evt in events)
    for rec in records:
        db.session.add(rec)
    db.session.flush()

    db_mock = mocker.patch('indico_livesync.uploader.db')

    uploader.run(records)

    objs = [(record.object, int(SimpleChange.created)) for record in records]
    assert uploader.all_uploaded == [objs[:3], objs[3:]]
    # All records should be marked as processed
    assert all(record.processed for record in records)
    # Marking records as processed is committed immediately
    assert db_mock.session.commit.call_count == 2


def test_run_failing(mocker, db, create_event, dummy_agent):
    """Test a failing queue run"""
    uploader = FailingUploader(MagicMock())
    uploader.BATCH_SIZE = 3

    events = tuple(create_event(id_=evt_id) for evt_id in range(10))
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event_id=evt.id,
                                       agent=dummy_agent)
                    for evt in events)

    for rec in records:
        db.session.add(rec)
    db.session.flush()

    db_mock = mocker.patch('indico_livesync.uploader.db')

    uploader.run(records)
    objs = [(record.object, int(SimpleChange.created)) for record in records]
    assert uploader.logger.exception.called
    # No uploads should happen after a failed batch
    assert uploader._uploaded == [objs[:3], objs[3:6]]
    # Only successful records should be marked as processed
    assert all(record.processed for record in records[:3])
    assert not any(record.processed for record in records[3:])
    # Only the first successful batch should have triggered a commit
    assert db_mock.session.commit.call_count == 1
