# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from operator import attrgetter
from unittest.mock import MagicMock

from indico_livesync.base import LiveSyncBackendBase
from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.simplify import SimpleChange, _process_cascaded_event_contents
from indico_livesync.uploader import Uploader


class RecordingUploader(Uploader):
    """An uploader which logs each 'upload'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uploaded = []
        self.logger = MagicMock()

    def upload_records(self, records, initial=False):
        self._uploaded = list(records)
        return True

    @property
    def all_uploaded(self):
        return self._uploaded


class FailingUploader(RecordingUploader):
    """An uploader where uploading fails."""

    def upload_records(self, records, initial=False):
        raise Exception('All your data are belong to us!')


class TestBackend(LiveSyncBackendBase):
    def __init__(self):
        super().__init__(MagicMock())
        self.plugin = MagicMock()


def test_run_initial(mocker):
    """Test the initial upload"""
    mocker.patch.object(Uploader, 'processed_records', autospec=True)
    mocker.patch('indico_livesync.uploader.verbose_iterator', new=lambda it, *a, **kw: it)
    uploader = RecordingUploader(MagicMock())
    records = tuple(MagicMock(id=evt_id) for evt_id in range(4))
    uploader.run_initial(records, 4)
    assert uploader.all_uploaded == [(record, SimpleChange.created) for record in records]
    # During an initial export there are no records to mark as processed
    assert not uploader.processed_records.called


def _sorted_process_cascaded_event_contents(records, additional_events=None, *, include_deleted=False,
                                            skip_all_deleted=False):
    return sorted(_process_cascaded_event_contents(records, additional_events), key=attrgetter('id'))


def test_run(mocker, monkeypatch, db, create_event, dummy_agent):
    """Test uploading queued data"""
    uploader = RecordingUploader(TestBackend())

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
    assert uploader.all_uploaded == objs
    # All records should be marked as processed
    assert all(record.processed for record in records)
    # After the queue run the changes should be committed
    assert db_mock.session.commit.call_count == 1


def test_run_failing(mocker, monkeypatch, db, create_event, dummy_agent):
    """Test a failing queue run"""
    uploader = FailingUploader(TestBackend())

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
    assert uploader.logger.exception.called
    # No uploads should happen after a failed batch
    assert not uploader._uploaded
    # No records should be marked as processed
    assert not any(record.processed for record in records)
    # And nothing should have been committed
    db_mock.session.commit.assert_not_called()
