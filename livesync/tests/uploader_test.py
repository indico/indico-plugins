# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from operator import attrgetter
from unittest.mock import MagicMock

from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.simplify import SimpleChange, _process_cascaded_event_contents
from indico_livesync.uploader import Uploader


class RecordingUploader(Uploader):
    """An uploader which logs each 'upload'"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uploaded = []
        self.logger = MagicMock()

    def upload_records(self, records, initial=False):
        self._uploaded.append(list(records))

    @property
    def all_uploaded(self):
        return self._uploaded


class FailingUploader(RecordingUploader):
    """An uploader where the second batch fails"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._n = 0

    def upload_records(self, records, initial=False):
        super().upload_records(records)
        self._n += 1
        if self._n == 2:
            raise Exception('All your data are belong to us!')


def test_run_initial(mocker):
    """Test the initial upload"""
    mocker.patch.object(Uploader, 'processed_records', autospec=True)
    mocker.patch('indico_livesync.uploader.verbose_iterator', new=lambda it, *a, **kw: it)
    uploader = RecordingUploader(MagicMock())
    records = tuple(MagicMock(id=evt_id) for evt_id in range(4))
    uploader.run_initial(records, 4)
    assert uploader.all_uploaded == [[(record, SimpleChange.created) for record in records]]
    # During an initial export there are no records to mark as processed
    assert not uploader.processed_records.called


def _sorted_process_cascaded_event_contents(records, additional_events=None):
    return sorted(_process_cascaded_event_contents(records, additional_events), key=attrgetter('id'))


def test_run(mocker, monkeypatch, db, create_event, dummy_agent):
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
    monkeypatch.setattr('indico_livesync.simplify._process_cascaded_event_contents',
                        _sorted_process_cascaded_event_contents)

    uploader.run(records)

    objs = [(record.object, int(SimpleChange.created)) for record in records]
    assert uploader.all_uploaded == [objs[:3], objs[3:]]
    assert len(uploader.all_uploaded[0]) == 3
    assert len(uploader.all_uploaded[1]) == 1
    # All records should be marked as processed
    assert all(record.processed for record in records)
    # After the queue run the changes should be committed
    assert db_mock.session.commit.call_count == 1


def test_run_failing(mocker, monkeypatch, db, create_event, dummy_agent):
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
    monkeypatch.setattr('indico_livesync.simplify._process_cascaded_event_contents',
                        _sorted_process_cascaded_event_contents)

    uploader.run(records)
    objs = [(record.object, int(SimpleChange.created)) for record in records]
    assert uploader.logger.exception.called
    # No uploads should happen after a failed batch
    assert uploader._uploaded == [objs[:3], objs[3:6]]
    # No records should be marked as processed
    assert not any(record.processed for record in records)
    # And nothing should have been committed
    db_mock.session.commit.assert_not_called()
