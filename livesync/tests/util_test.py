# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

from indico.util.date_time import now_utc

from indico_livesync.models.queue import ChangeType, EntryType, LiveSyncQueueEntry
from indico_livesync.plugin import LiveSyncPlugin
from indico_livesync.util import clean_old_entries, get_excluded_categories


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
    assert LiveSyncQueueEntry.query.count() == 20
    # Nothing deleted when explicitly set to 0 (which is the default)
    LiveSyncPlugin.settings.set('queue_entry_ttl', 0)
    clean_old_entries()
    assert LiveSyncQueueEntry.query.count() == 20
    # Only the correct entries deleted, and no unprocessed ones
    LiveSyncPlugin.settings.set('queue_entry_ttl', 3)
    clean_old_entries()
    assert LiveSyncQueueEntry.query.filter_by(processed=False).count() == 10
    assert LiveSyncQueueEntry.query.filter_by(processed=True).count() == 3


def test_get_excluded_categories(dummy_category, create_category):
    cat1 = create_category()
    cat1a = create_category(parent=cat1)
    cat1aa = create_category(parent=cat1a)
    cat1b = create_category(parent=cat1)
    cat2 = create_category()
    LiveSyncPlugin.settings.set('excluded_categories', [{'id': cat1.id}])
    assert get_excluded_categories() == {cat1.id}
    assert get_excluded_categories(deep=True) == {cat1.id, cat1a.id, cat1aa.id, cat1b.id}
    LiveSyncPlugin.settings.set('excluded_categories', [{'id': 0}])
    assert get_excluded_categories() == {0}
    assert get_excluded_categories(deep=True) == {cat1.id, cat1a.id, cat1aa.id, cat1b.id, cat2.id, dummy_category.id, 0}
