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
