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

import pytest

from indico.modules.categories import Category

from indico_livesync.models.queue import ChangeType, LiveSyncQueueEntry
from indico_livesync.util import get_excluded_categories, obj_ref


CATEGORY_PARENTS = {
    0: None,
    1: 0,
    2: 0,
    3: 2,
    4: 3,
    5: 3
}


@pytest.mark.usefixtures('dummy_agent')
def test_excluded_categories(mocker, monkeypatch, db, create_category):
    """Test if category exclusions work."""
    plugin = mocker.patch('indico_livesync.plugin.LiveSyncPlugin')
    plugin.settings.get.return_value = [{'id': 2}, {'id': 3}]

    categories = {}
    with db.session.no_autoflush:
        for cat_id in xrange(6):
            category = (create_category(cat_id, title=str(cat_id), protection_mode=0,
                                        parent=categories[CATEGORY_PARENTS[cat_id]])
                        if cat_id else Category.get_root())
            categories[cat_id] = category
            db.session.add(category)
            db.session.flush()

    db.session.flush()

    for cat in categories.viewvalues():
        db = mocker.patch('indico_livesync.models.queue.db')
        LiveSyncQueueEntry.create({ChangeType.created}, obj_ref(cat), excluded_categories=get_excluded_categories())
        assert db.session.add.called == (cat.id not in {2, 3, 4, 5})
