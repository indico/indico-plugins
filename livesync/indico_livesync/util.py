# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from indico.util.caching import memoize_request
from indico.util.date_time import now_utc
from MaKaC.conference import Conference, Contribution, SubContribution, Category, CategoryManager, ConferenceHolder


def obj_ref(obj, parent=None):
    """Returns a tuple identifying a category/event/contrib/subcontrib"""
    if isinstance(obj, Category):
        ref = {'type': 'category', 'category_id': obj.id}
    elif isinstance(obj, Conference):
        ref = {'type': 'event', 'category_id': obj.getOwner().id, 'event_id': obj.id}
    elif isinstance(obj, Contribution):
        event = parent or obj.getConference()
        ref = {'type': 'contribution', 'category_id': event.getOwner().id, 'event_id': event.id, 'contrib_id': obj.id}
    elif isinstance(obj, SubContribution):
        contrib = parent or obj.getContribution()
        event = contrib.getConference()
        ref = {'type': 'subcontribution',
               'category_id': event.getOwner().id,
               'event_id': event.id, 'contrib_id': contrib.id, 'subcontrib_id': obj.id}
    else:
        raise ValueError('Unexpected object: {}'.format(obj.__class__.__name__))
    return ImmutableDict(ref)


def obj_deref(ref):
    """Returns the object identified by `ref`"""
    if ref['type'] == 'category':
        try:
            return CategoryManager().getById(ref['category_id'])
        except KeyError:
            return None
    elif ref['type'] in {'event', 'contribution', 'subcontribution'}:
        event = ConferenceHolder().getById(ref['event_id'], quiet=True)
        if ref['type'] == 'event' or not event:
            return event
        contrib = event.getContributionById(ref['contrib_id'])
        if ref['type'] == 'contribution' or not contrib:
            return contrib
        return contrib.getSubContributionById(ref['subcontrib_id'])
    else:
        raise ValueError('Unexpected object type: {}'.format(ref['type']))


def make_compound_id(ref):
    """Returns the compound ID for the referenced object"""
    if ref['type'] == 'category':
        raise ValueError('Compound IDs are not supported for categories')
    elif ref['type'] == 'event':
        return ref['event_id']
    elif ref['type'] == 'contribution':
        return '{}.{}'.format(ref['event_id'], ref['contrib_id'])
    elif ref['type'] == 'subcontribution':
        return '{}.{}.{}'.format(ref['event_id'], ref['contrib_id'], ref['subcontrib_id'])
    else:
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
    return ref['category_id'] in get_excluded_categories()
