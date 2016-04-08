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

from __future__ import unicode_literals

from datetime import timedelta

from werkzeug.datastructures import ImmutableDict

from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.util.caching import memoize_request
from indico.util.date_time import now_utc
from MaKaC.conference import Category, CategoryManager, Conference


def obj_ref(obj):
    """Returns a tuple identifying a category/event/contrib/subcontrib"""
    from indico_livesync.models.queue import EntryType
    if isinstance(obj, Category):
        ref = {'type': EntryType.category, 'category_id': obj.id}
    elif isinstance(obj, Event):
        ref = {'type': EntryType.event, 'event_id': obj.id}
    elif isinstance(obj, Conference):
        ref = {'type': EntryType.event, 'event_id': int(obj.id)}
    elif isinstance(obj, Contribution):
        ref = {'type': EntryType.contribution, 'contrib_id': obj.id}
    elif isinstance(obj, SubContribution):
        ref = {'type': EntryType.subcontribution, 'subcontrib_id': obj.id}
    else:
        raise ValueError('Unexpected object: {}'.format(obj.__class__.__name__))
    return ImmutableDict(ref)


def obj_deref(ref):
    """Returns the object identified by `ref`"""
    from indico_livesync.models.queue import EntryType
    if ref['type'] == EntryType.category:
        return CategoryManager().getById(ref['category_id'], True)
    elif ref['type'] == EntryType.event:
        return Event.get(ref['event_id'])
    elif ref['type'] == EntryType.contribution:
        return Contribution.get(ref['contrib_id'])
    elif ref['type'] == EntryType.subcontribution:
        return SubContribution.get(ref['subcontrib_id'])
    else:
        raise ValueError('Unexpected object type: {}'.format(ref['type']))


def make_compound_id(ref):
    """Returns the compound ID for the referenced object"""
    from indico_livesync.models.queue import EntryType
    if ref['type'] == EntryType.category:
        raise ValueError('Compound IDs are not supported for categories')
    obj = obj_deref(ref)
    if isinstance(obj, Event):
        return unicode(obj.id)
    elif isinstance(obj, Contribution):
        return '{}.{}'.format(obj.event_id, obj.id)
    elif isinstance(obj, SubContribution):
        return '{}.{}.{}'.format(obj.contribution.event_id, obj.contribution_id, obj.id)
    raise ValueError('Unexpected object type: {}'.format(ref['type']))


def clean_old_entries():
    """Deletes obsolete entries from the queues"""
    from indico_livesync.plugin import LiveSyncPlugin
    from indico_livesync.models.queue import LiveSyncQueueEntry

    queue_entry_ttl = LiveSyncPlugin.settings.get('queue_entry_ttl')
    if not queue_entry_ttl:
        return
    expire_threshold = now_utc() - timedelta(days=queue_entry_ttl)
    LiveSyncQueueEntry.find(LiveSyncQueueEntry.processed,
                            LiveSyncQueueEntry.timestamp < expire_threshold).delete(synchronize_session='fetch')


@memoize_request
def get_excluded_categories():
    """Get all excluded category IDs"""
    from indico_livesync.plugin import LiveSyncPlugin
    todo = {x['id'] for x in LiveSyncPlugin.settings.get('excluded_categories')}
    excluded = set()
    while todo:
        category_id = todo.pop()
        try:
            category = CategoryManager().getById(category_id)
        except KeyError:
            continue
        excluded.add(category.getId())
        todo.update(category.subcategories)
    return excluded


def is_ref_excluded(ref):
    from indico_livesync.models.queue import EntryType
    if ref['type'] == EntryType.category:
        return ref['category_id'] in get_excluded_categories()
    else:
        obj = obj_deref(ref)
        return unicode(obj.event_new.category_id) in {unicode(x) for x in get_excluded_categories()}
