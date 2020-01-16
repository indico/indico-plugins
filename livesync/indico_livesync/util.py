# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from datetime import timedelta

from werkzeug.datastructures import ImmutableDict

from indico.modules.categories.models.categories import Category
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.sessions.models.sessions import Session
from indico.util.caching import memoize_request
from indico.util.date_time import now_utc


def obj_ref(obj):
    """Returns a tuple identifying a category/event/contrib/subcontrib"""
    from indico_livesync.models.queue import EntryType
    if isinstance(obj, Category):
        ref = {'type': EntryType.category, 'category_id': obj.id}
    elif isinstance(obj, Event):
        ref = {'type': EntryType.event, 'event_id': obj.id}
    elif isinstance(obj, Session):
        ref = {'type': EntryType.session, 'session_id': obj.id}
    elif isinstance(obj, Contribution):
        ref = {'type': EntryType.contribution, 'contrib_id': obj.id}
    elif isinstance(obj, SubContribution):
        ref = {'type': EntryType.subcontribution, 'subcontrib_id': obj.id}
    else:
        raise ValueError('Unexpected object: {}'.format(obj.__class__.__name__))
    return ImmutableDict(ref)


@memoize_request
def obj_deref(ref):
    """Returns the object identified by `ref`"""
    from indico_livesync.models.queue import EntryType
    if ref['type'] == EntryType.category:
        return Category.get_one(ref['category_id'])
    elif ref['type'] == EntryType.event:
        return Event.get_one(ref['event_id'])
    elif ref['type'] == EntryType.session:
        return Session.get_one(ref['session_id'])
    elif ref['type'] == EntryType.contribution:
        return Contribution.get_one(ref['contrib_id'])
    elif ref['type'] == EntryType.subcontribution:
        return SubContribution.get_one(ref['subcontrib_id'])
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
    """Get excluded category IDs."""
    from indico_livesync.plugin import LiveSyncPlugin
    return {int(x['id']) for x in LiveSyncPlugin.settings.get('excluded_categories')}


def compound_id(obj):
    """Generate a hierarchical compound ID, separated by dots."""
    if isinstance(obj, (Category, Session)):
        raise TypeError('Compound IDs are not supported for this entry type')
    elif isinstance(obj, Event):
        return unicode(obj.id)
    elif isinstance(obj, Contribution):
        return '{}.{}'.format(obj.event_id, obj.id)
    elif isinstance(obj, SubContribution):
        return '{}.{}.{}'.format(obj.contribution.event_id, obj.contribution_id, obj.id)
