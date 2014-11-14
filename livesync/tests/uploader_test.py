# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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
from mock import MagicMock

from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType
from indico_livesync.uploader import Uploader, MARCXMLUploader


class RecordingUploader(Uploader):
    """An uploader which logs each 'upload'"""
    def __init__(self, *args, **kwargs):
        super(RecordingUploader, self).__init__(*args, **kwargs)
        self._uploaded = []

    def upload_records(self, records, from_queue):
        self._uploaded.append((records, from_queue))


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


def create_mock_agent(has_task=False):
    agent = MagicMock()
    if not has_task:
        agent.task = None
    # else we use the default mock attribute
    return agent


def test_run_initial(mocker):
    """Test the initial upload"""
    mocker.patch.object(Uploader, 'processed_records', autospec=True)
    uploader = RecordingUploader(create_mock_agent())
    uploader.INITIAL_BATCH_SIZE = 3
    events = tuple(range(4))
    uploader.run_initial(events)
    # We expect two batches, with the second one being smaller (i.e. no None padding, just the events)
    batches = events[:3], events[3:]
    assert len(batches[0]) > len(batches[1])
    assert uploader._uploaded == [(batches[0], False), (batches[1], False)]
    # During an initial export there are no records to mark as processed
    assert not uploader.processed_records.called


def test_run(mocker):
    """Test uploading queued data"""
    db = mocker.patch('indico_livesync.uploader.db')
    uploader = RecordingUploader(create_mock_agent())
    uploader.BATCH_SIZE = 3
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created) for _ in xrange(4))
    uploader.run(records)
    batches = records[:3], records[3:]
    assert uploader._uploaded == [(batches[0], True), (batches[1], True)]
    # All records should be marked as processed
    assert all(record.processed for record in records)
    # Marking records as processed is committed immediately
    assert db.session.commit.call_count == 2


def test_run_extend_task(mocker):
    """Test if the task is extended"""
    mocker.patch('indico_livesync.uploader.db')
    uploader = RecordingUploader(create_mock_agent(has_task=True))
    uploader.BATCH_SIZE = 3
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created) for _ in xrange(4))
    uploader.run(records)
    assert uploader.agent.task.extend_runtime.call_count == 2


def test_run_failing(mocker):
    """Test a failing queue run"""
    db = mocker.patch('indico_livesync.uploader.db')
    uploader = FailingUploader(create_mock_agent())
    uploader.BATCH_SIZE = 3
    records = tuple(LiveSyncQueueEntry(change=ChangeType.created) for _ in xrange(10))
    with pytest.raises(Exception):
        uploader.run(records)
    # No uploads should bappen after a failed batch
    assert uploader._uploaded == [(records[:3], True), (records[3:6], True)]
    # Only successful records should be marked as processed
    assert all(record.processed for record in records[:3])
    assert not any(record.processed for record in records[3:])
    # Only the first uccessful batch should have triggered a commit
    assert db.session.commit.call_count == 1


def test_marcxml_run(mocker):
    """Text if the MARCXML uploader uses the correct function"""
    mocker.patch('indico_livesync.uploader.db')
    mocker.patch.object(MARCXMLUploader, 'upload_xml', autospec=True)
    mxg = mocker.patch('indico_livesync.uploader.MARCXMLGenerator')
    uploader = MARCXMLUploader(create_mock_agent())
    uploader.run([LiveSyncQueueEntry(change=ChangeType.created)])
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
    uploader = MARCXMLUploader(create_mock_agent())
    uploader.run_initial([1])
    assert not uploader.upload_xml.called
