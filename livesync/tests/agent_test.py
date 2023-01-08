# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from unittest.mock import MagicMock

import pytest

from indico_livesync.base import LiveSyncBackendBase
from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.plugin import LiveSyncPlugin


class DummyBackend(LiveSyncBackendBase):
    """Dummy agent

    A dummy agent for testing
    """

    def _precache_categories(self):
        pass


class NonDescriptiveAgent(LiveSyncBackendBase):
    """Nondescriptive agent"""


def test_title_description():
    """Test if title/description are extracted from docstring"""
    assert DummyBackend.title == 'Dummy agent'
    assert DummyBackend.description == 'A dummy agent for testing'
    assert NonDescriptiveAgent.title == 'Nondescriptive agent'
    assert NonDescriptiveAgent.description == 'no description available'


def test_run(mocker):
    """Test if run calls the fetcher/uploader properly"""
    mocker.patch.object(DummyBackend, 'fetch_records')
    backend = DummyBackend(MagicMock())
    mock_uploader = MagicMock()
    backend.uploader = lambda *x, **kw: mock_uploader
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


@pytest.mark.parametrize('disabled', (True, False))
@pytest.mark.parametrize('whitelisted', (True, False))
def test_fetch_records_categories_disabled(db, dummy_event, dummy_category, dummy_agent, disabled, whitelisted):
    """Test if the correct records are fetched"""
    backend = DummyBackend(dummy_agent)
    queue = [
        LiveSyncQueueEntry(change=ChangeType.protection_changed, type=EntryType.category, category=dummy_category),
        LiveSyncQueueEntry(change=ChangeType.created, type=EntryType.event, event=dummy_event)
    ]
    dummy_agent.queue = queue
    LiveSyncPlugin.settings.set('skip_category_changes', disabled)
    db.session.flush()
    expected = queue[1:] if disabled and not whitelisted else queue
    whitelist = (dummy_category.id,) if whitelisted else ()
    assert backend.fetch_records(whitelist) == expected
