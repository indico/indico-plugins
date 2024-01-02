# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from datetime import timedelta

from werkzeug.datastructures import ImmutableDict

from indico.core.db import db
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.categories import Category
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.events.sessions.models.sessions import Session
from indico.util.caching import memoize_request
from indico.util.date_time import now_utc


def obj_ref(obj):
    """Return a tuple identifying a category/event/contrib/subcontrib/note."""
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
    elif isinstance(obj, EventNote):
        ref = {'type': EntryType.note, 'note_id': obj.id}
    elif isinstance(obj, Attachment):
        ref = {'type': EntryType.attachment, 'attachment_id': obj.id}
    else:
        raise TypeError(f'Unexpected object: {obj.__class__.__name__}')
    return ImmutableDict(ref)


@memoize_request
def obj_deref(ref):
    """Return the object identified by `ref`."""
    from indico_livesync.models.queue import EntryType
    if ref['type'] == EntryType.category:
        return Category.get_or_404(ref['category_id'])
    elif ref['type'] == EntryType.event:
        return Event.get_or_404(ref['event_id'])
    elif ref['type'] == EntryType.session:
        return Session.get_or_404(ref['session_id'])
    elif ref['type'] == EntryType.contribution:
        return Contribution.get_or_404(ref['contrib_id'])
    elif ref['type'] == EntryType.subcontribution:
        return SubContribution.get_or_404(ref['subcontrib_id'])
    elif ref['type'] == EntryType.note:
        return EventNote.get_or_404(ref['note_id'])
    elif ref['type'] == EntryType.attachment:
        return Attachment.get_or_404(ref['attachment_id'])
    else:
        raise ValueError('Unexpected object type: {}'.format(ref['type']))


def clean_old_entries():
    """Delete obsolete entries from the queues."""
    from indico_livesync.models.queue import LiveSyncQueueEntry
    from indico_livesync.plugin import LiveSyncPlugin

    queue_entry_ttl = LiveSyncPlugin.settings.get('queue_entry_ttl')
    if not queue_entry_ttl:
        return
    expire_threshold = now_utc() - timedelta(days=queue_entry_ttl)
    LiveSyncQueueEntry.query.filter(LiveSyncQueueEntry.processed,
                                    LiveSyncQueueEntry.timestamp < expire_threshold).delete(synchronize_session='fetch')


@memoize_request
def get_excluded_categories(*, deep=False):
    """Get excluded category IDs.

    :param deep: Whether to get all subcategory ids as well
    """
    from indico_livesync.plugin import LiveSyncPlugin
    ids = {int(x['id']) for x in LiveSyncPlugin.settings.get('excluded_categories')}
    if not deep or not ids:
        return ids
    cte = Category.get_tree_cte()
    query = (db.session.query(Category.id)
             .join(cte, Category.id == cte.c.id)
             .filter(cte.c.path.overlap(ids), ~cte.c.is_deleted))
    return {x.id for x in query}
