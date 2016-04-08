# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
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

import pytest

from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.util.date_time import now_utc

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType, EntryType
from indico_livesync.plugin import LiveSyncPlugin
from indico_livesync.util import make_compound_id, clean_old_entries, get_excluded_categories


class MockCategory(object):
    def __init__(self, id_, subcategories=None):
        self.id = id_
        self.subcategories = subcategories or set()

    def getId(self):
        return self.id


class MockCategoryManager(object):
    # a
    # |- b
    # `- c
    #    |- d
    #       |- e
    #       `- f
    categories = {
        'a': MockCategory('a', {'b', 'c'}),
        'b': MockCategory('b'),
        'c': MockCategory('c', {'d'}),
        'd': MockCategory('d', {'e', 'f'}),
        'e': MockCategory('e'),
        'f': MockCategory('f')
    }

    @classmethod
    def getById(cls, id_):
        return cls.categories[id_]


@pytest.mark.parametrize(('ref', 'expected'), (
    ({'type': EntryType.event, 'event_id': '123'}, '123'),
    ({'type': EntryType.contribution, 'contrib_id': '456'}, '123.456'),
    ({'type': EntryType.subcontribution, 'subcontrib_id': '789'}, '123.456.789'),
))
def test_make_compound_id(create_event, ref, expected):
    evt = create_event(123)
    evt.contributions = [Contribution(id=456, title='test', duration=timedelta(hours=1))]
    evt.contributions[0].subcontributions = [SubContribution(id=789, title='foo', duration=timedelta(minutes=10))]
    assert make_compound_id(ref) == expected


@pytest.mark.parametrize('ref_type', ('unknown', 'category'))
def test_make_compound_id_errors(ref_type):
    with pytest.raises(ValueError):
        make_compound_id({'type': ref_type})


def test_clean_old_entries(dummy_event_new, db):
    now = now_utc()
    agent = LiveSyncAgent(name='dummy', backend_name='dummy')
    for processed in (True, False):
        for day in range(10):
            db.session.add(LiveSyncQueueEntry(agent=agent, change=ChangeType.created, type=EntryType.event,
                                              event=dummy_event_new, processed=processed,
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


def test_excluded_categories(mocker, monkeypatch):
    """Test if category exclusions work"""
    monkeypatch.setattr('indico_livesync.util.CategoryManager', MockCategoryManager)
    plugin = mocker.patch('indico_livesync.plugin.LiveSyncPlugin')
    plugin.settings.get.return_value = [{'id': 'invalid'}, {'id': 'c'}, {'id': 'd'}]
    assert get_excluded_categories() == {'c', 'd', 'e', 'f'}
