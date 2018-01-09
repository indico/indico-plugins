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

from mock import MagicMock, Mock

from indico.modules.events import Event

from indico_livesync import SimpleChange
from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.uploader import MARCXMLUploader, Uploader


class RecordingUploader(Uploader):
    """An uploader which logs each 'upload'"""
    def __init__(self, *args, **kwargs):
        super(RecordingUploader, self).__init__(*args, **kwargs)
        self._uploaded = []
        self.logger = MagicMock()

    def upload_records(self, records, from_queue):
        if from_queue:
            recs = set(records.viewitems())
            self._uploaded.append((recs, from_queue))
        else:
            self._uploaded.append((set(records), from_queue))

    @property
    def all_uploaded(self):
        return self._uploaded


class FailingUploader(RecordingUploader):
    """An uploader where the second batch fails"""
    def __init__(self, *args, **kwargs):
        super(FailingUploader, self).__init__(*args, **kwargs)
        self._n = 0

    def upload_records(self, records, from_queue):
        super(FailingUploader, self).upload_records(records, from_queue)
        self._n += 1
        if self._n == 2:
            raise Exception('All your data are belong to us!')


def test_run_initial(mocker):
    """Test the initial upload"""
    mocker.patch.object(Uploader, 'processed_records', autospec=True)
    uploader = RecordingUploader(MagicMock())
    uploader.INITIAL_BATCH_SIZE = 3
    records = tuple(Mock(spec=Event, id=evt_id) for evt_id in xrange(4))
    uploader.run_initial(records)
    # We expect two batches, with the second one being smaller (i.e. no None padding, just the events)
    batches = set(records[:3]), set(records[3:])
    assert uploader.all_uploaded == [(batches[0], False), (batches[1], False)]
    # During an initial export there are no records to mark as processed
    assert not uploader.processed_records.called


def test_run(mocker, db, create_event, dummy_agent):
    """Test uploading queued data"""
    uploader = RecordingUploader(MagicMock())
    uploader.BATCH_SIZE = 3

    events = tuple(create_event(id_=evt_id) for evt_id in xrange(4))
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event_id=evt.id,
                                       agent=dummy_agent)
                    for evt in events)
    for rec in records:
        db.session.add(rec)
    db.session.flush()

    db_mock = mocker.patch('indico_livesync.uploader.db')

    uploader.run(records)

    objs = tuple((record.object, int(SimpleChange.created)) for record in records)
    batches = set(objs[:3]), set(objs[3:])
    assert uploader.all_uploaded == [(batches[0], True), (batches[1], True)]
    # All records should be marked as processed
    assert all(record.processed for record in records)
    # Marking records as processed is committed immediately
    assert db_mock.session.commit.call_count == 2


def test_run_failing(mocker, db, create_event, dummy_agent):
    """Test a failing queue run"""
    uploader = FailingUploader(MagicMock())
    uploader.BATCH_SIZE = 3

    events = tuple(create_event(id_=evt_id) for evt_id in xrange(10))
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event_id=evt.id,
                                       agent=dummy_agent)
                    for evt in events)

    for rec in records:
        db.session.add(rec)
    db.session.flush()

    db_mock = mocker.patch('indico_livesync.uploader.db')

    uploader.run(records)
    objs = tuple((record.object, int(SimpleChange.created)) for record in records)
    assert uploader.logger.exception.called
    # No uploads should happen after a failed batch
    assert uploader._uploaded == [(set(objs[:3]), True), (set(objs[3:6]), True)]
    # Only successful records should be marked as processed
    assert all(record.processed for record in records[:3])
    assert not any(record.processed for record in records[3:])
    # Only the first uccessful batch should have triggered a commit
    assert db_mock.session.commit.call_count == 1


def test_marcxml_run(mocker, db, dummy_event, dummy_agent):
    """Text if the MARCXML uploader uses the correct function"""
    mocker.patch('indico_livesync.uploader.db')
    mocker.patch.object(MARCXMLUploader, 'upload_xml', autospec=True)
    mxg = mocker.patch('indico_livesync.uploader.MARCXMLGenerator')

    entry = LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event=dummy_event,
                               agent=dummy_agent)
    db.session.add(entry)
    db.session.flush()

    uploader = MARCXMLUploader(MagicMock())
    uploader.run([entry])
    assert mxg.records_to_xml.called
    assert not mxg.objects_to_xml.called
    assert uploader.upload_xml.called
    mxg.reset_mock()
    uploader.run_initial([1])
    assert not mxg.records_to_xml.called
    assert mxg.objects_to_xml.called
    assert uploader.upload_xml.called


def test_marcxml_empty_result(mocker):
    """Test if the MARCXML uploader doesn't upload empty records"""
    mocker.patch('indico_livesync.uploader.MARCXMLGenerator.objects_to_xml', return_value=None)
    mocker.patch.object(MARCXMLUploader, 'upload_xml', autospec=True)
    uploader = MARCXMLUploader(MagicMock())
    uploader.run_initial([1])
    assert not uploader.upload_xml.called
