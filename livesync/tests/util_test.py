# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

from indico.util.date_time import now_utc

from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.plugin import LiveSyncPlugin
from indico_livesync.util import clean_old_entries


def test_clean_old_entries(dummy_event, db, dummy_agent):
    now = now_utc()
    for processed in (True, False):
        for day in range(10):
            db.session.add(LiveSyncQueueEntry(agent=dummy_agent, change=ChangeType.created, type=EntryType.event,
                                              event=dummy_event, processed=processed,
                                              timestamp=now - timedelta(days=day, hours=12)))
    db.session.flush()
    # Nothing deleted with the setting's default value
    clean_old_entries()
    assert LiveSyncQueueEntry.find().count() == 20
    # Nothing deleted when explicitly set to 0 (which is the default)
    LiveSyncPlugin.settings.set('queue_entry_ttl', 0)
    clean_old_entries()
    assert LiveSyncQueueEntry.find().count() == 20
    # Only the correct entries deleted, and no unprocessed ones
    LiveSyncPlugin.settings.set('queue_entry_ttl', 3)
    clean_old_entries()
    assert LiveSyncQueueEntry.find(processed=False).count() == 10
    assert LiveSyncQueueEntry.find(processed=True).count() == 3
