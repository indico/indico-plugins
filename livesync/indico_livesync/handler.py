# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

from collections import defaultdict

from flask import g
from sqlalchemy import inspect

from indico.core import signals
from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.modules.categories.models.categories import Category
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.sessions import Session
from indico.util.event import unify_event_args

from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType
from indico_livesync.util import obj_ref, get_excluded_categories


def connect_signals(plugin):
    # request
    plugin.connect(signals.after_process, _apply_changes)
    plugin.connect(signals.before_retry, _clear_changes)
    # moved
    plugin.connect(signals.category.moved, _moved)
    plugin.connect(signals.event.moved, _moved)
    # created
    plugin.connect(signals.event.created, _created)
    plugin.connect(signals.event.contribution_created, _created)
    plugin.connect(signals.event.subcontribution_created, _created)
    # deleted
    plugin.connect(signals.event.deleted, _deleted)
    plugin.connect(signals.event.contribution_deleted, _deleted)
    plugin.connect(signals.event.subcontribution_deleted, _deleted)
    # updated
    plugin.connect(signals.event.data_changed, _updated)
    plugin.connect(signals.event.contribution_updated, _updated)
    plugin.connect(signals.event.subcontribution_updated, _updated)
    # timetable
    plugin.connect(signals.event.timetable_entry_created, _timetable_changed)
    plugin.connect(signals.event.timetable_entry_updated, _timetable_changed)
    plugin.connect(signals.event.timetable_entry_deleted, _timetable_changed)
    # protection
    plugin.connect(signals.acl.protection_changed, _category_protection_changed, sender=Category)
    plugin.connect(signals.acl.protection_changed, _protection_changed, sender=Event)
    plugin.connect(signals.acl.protection_changed, _protection_changed, sender=Session)
    plugin.connect(signals.acl.protection_changed, _protection_changed, sender=Contribution)
    # ACLs
    plugin.connect(signals.acl.entry_changed, _protection_changed, sender=Category)
    plugin.connect(signals.acl.entry_changed, _protection_changed, sender=Event)
    plugin.connect(signals.acl.entry_changed, _protection_changed, sender=Session)
    plugin.connect(signals.acl.entry_changed, _protection_changed, sender=Contribution)
    # notes
    plugin.connect(signals.event.notes.note_added, _note_changed)
    plugin.connect(signals.event.notes.note_deleted, _note_changed)
    plugin.connect(signals.event.notes.note_modified, _note_changed)
    # attachments
    plugin.connect(signals.attachments.folder_deleted, _attachment_changed)
    plugin.connect(signals.attachments.attachment_created, _attachment_changed)
    plugin.connect(signals.attachments.attachment_deleted, _attachment_changed)
    plugin.connect(signals.attachments.attachment_updated, _attachment_changed)


def _moved(obj, old_parent, **kwargs):
    _register_change(obj, ChangeType.moved)
    category_protection = old_parent.effective_protection_mode
    new_category_protection = obj.protection_parent.effective_protection_mode

    # Event is inheriting and protection of new parent is different
    if category_protection != new_category_protection and obj.is_inheriting:
        _register_change(obj, ChangeType.protection_changed)


def _created(obj, **kwargs):
    if isinstance(obj, Event):
        parent = None
    elif isinstance(obj, Contribution):
        parent = obj.event_new
    elif isinstance(obj, SubContribution):
        parent = obj.contribution
    else:
        raise TypeError('Unexpected object: {}'.format(type(obj).__name__))
    if parent:
        _register_change(parent, ChangeType.data_changed)
    _register_change(obj, ChangeType.created)


@unify_event_args
def _deleted(obj, **kwargs):
    _register_deletion(obj)


def _updated(obj, **kwargs):
    _register_change(obj, ChangeType.data_changed)


def _timetable_changed(entry, **kwargs):
    _register_change(entry.event_new, ChangeType.data_changed)


def _category_protection_changed(sender, obj, mode, old_mode, **kwargs):
    parent_mode = obj.protection_parent.effective_protection_mode
    if ((old_mode == ProtectionMode.inheriting and parent_mode == mode) or
            (old_mode == parent_mode and mode == ProtectionMode.inheriting)):
        return
    _protection_changed(sender, obj, mode=mode, old_mode=old_mode, **kwargs)


def _protection_changed(sender, obj, **kwargs):
    if not inspect(obj).persistent:
        return
    _register_change(obj, ChangeType.protection_changed)


def _note_changed(note, **kwargs):
    obj = note.event_new if isinstance(note.object, Session) else note.object
    _register_change(obj, ChangeType.data_changed)


def _attachment_changed(attachment_or_folder, **kwargs):
    folder = getattr(attachment_or_folder, 'folder', attachment_or_folder)
    if not isinstance(folder.object, Category) and not isinstance(folder.object, Session):
        _register_change(folder.object.event_new, ChangeType.data_changed)


def _apply_changes(sender, **kwargs):
    excluded_categories = get_excluded_categories()

    if not hasattr(g, 'livesync_changes'):
        return
    for ref, changes in g.livesync_changes.iteritems():
        LiveSyncQueueEntry.create(changes, ref, excluded_categories=excluded_categories)


def _clear_changes(sender, **kwargs):
    if not hasattr(g, 'livesync_changes'):
        return
    del g.livesync_changes


def _register_deletion(obj):
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(ChangeType.deleted)


@unify_event_args
def _register_change(obj, action):
    if not isinstance(obj, Category):
        event = obj.event_new
        if event is None or event.is_deleted or event.as_legacy is None:
            # When deleting an event we get data change signals afterwards. We can simple ignore them.
            # Also, ACL changes during user merges might involve deleted objects which we also don't care about
            return
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(action)


def _init_livesync_g():
    g.setdefault('livesync_changes', defaultdict(set))
