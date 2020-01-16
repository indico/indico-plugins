# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from mock import MagicMock

from indico_livesync.base import LiveSyncBackendBase
from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry


class DummyBackend(LiveSyncBackendBase):
    """Dummy agent

    A dummy agent for testing
    """


class NonDescriptiveAgent(LiveSyncBackendBase):
    """Nondescriptive agent"""


def test_title_description():
    """Test if title/description are extracted from docstring"""
    assert DummyBackend.title == 'Dummy agent'
    assert DummyBackend.description == 'A dummy agent for testing'
    assert NonDescriptiveAgent.title == 'Nondescriptive agent'
    assert NonDescriptiveAgent.description == 'no description available'


def test_run_initial():
    """Test if run_initial_export calls the uploader properly"""
    backend = DummyBackend(MagicMock())
    mock_uploader = MagicMock()
    backend.uploader = lambda x: mock_uploader
    events = object()
    backend.run_initial_export(events)
    mock_uploader.run_initial.assert_called_with(events)


def test_run(mocker):
    """Test if run calls the fetcher/uploader properly"""
    mocker.patch.object(DummyBackend, 'fetch_records')
    backend = DummyBackend(MagicMock())
    mock_uploader = MagicMock()
    backend.uploader = lambda x: mock_uploader
    backend.run()
    assert backend.fetch_records.called
    assert mock_uploader.run.called


def test_fetch_records(db, dummy_event, dummy_agent):
    """Test if the correct records are fetched"""
    backend = DummyBackend(dummy_agent)
    queue = [
        LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event=dummy_event, processed=True),
        LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event=dummy_event)
    ]
    dummy_agent.queue = queue
    db.session.flush()
    assert backend.fetch_records() == [queue[1]]
