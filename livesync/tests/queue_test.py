# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
