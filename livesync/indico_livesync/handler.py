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

from collections import defaultdict

from flask import g
from sqlalchemy import inspect

from indico.core import signals
from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.sessions import Session
from indico.util.event import unify_event_args
from MaKaC.accessControl import AccessController
from MaKaC.conference import Category, ConferenceHolder, Conference

from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType
from indico_livesync.util import obj_ref, is_ref_excluded


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
    plugin.connect(signals.category.protection_changed, _protection_changed_legacy)
    plugin.connect(signals.event.protection_changed, _protection_changed_legacy)
    plugin.connect(signals.acl.protection_changed, _protection_changed, sender=Session)
    plugin.connect(signals.acl.protection_changed, _protection_changed, sender=Contribution)
    # ACLs
    plugin.connect(signals.acl.access_granted, _acl_changed_legacy)
    plugin.connect(signals.acl.access_revoked, _acl_changed_legacy)
    plugin.connect(signals.acl.modification_granted, _acl_changed_legacy)
    plugin.connect(signals.acl.modification_revoked, _acl_changed_legacy)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Event)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Session)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Contribution)
    # domain access
    plugin.connect(signals.category.domain_access_granted, _domain_changed)
    plugin.connect(signals.category.domain_access_revoked, _domain_changed)
    plugin.connect(signals.event.domain_access_granted, _domain_changed)
    plugin.connect(signals.event.domain_access_revoked, _domain_changed)
    # notes
    plugin.connect(signals.event.notes.note_added, _note_changed)
    plugin.connect(signals.event.notes.note_deleted, _note_changed)
    plugin.connect(signals.event.notes.note_modified, _note_changed)
    # attachments
    plugin.connect(signals.attachments.folder_deleted, _attachment_changed)
    plugin.connect(signals.attachments.attachment_created, _attachment_changed)
    plugin.connect(signals.attachments.attachment_deleted, _attachment_changed)
    plugin.connect(signals.attachments.attachment_updated, _attachment_changed)


def _moved(obj, old_parent, new_parent, **kwargs):
    _register_change(obj, ChangeType.moved)
    category_protection = old_parent.isProtected()
    new_category_protection = new_parent.isProtected()

    if category_protection != new_category_protection and obj.getAccessProtectionLevel() == 0:
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


def _deleted(obj, **kwargs):
    _register_deletion(obj)


def _updated(obj, **kwargs):
    _register_change(obj, ChangeType.data_changed)


def _timetable_changed(entry, **kwargs):
    _register_change(entry.event_new, ChangeType.data_changed)


def _protection_changed_legacy(obj, old, new, **kwargs):
    if new == 0:  # inheriting
        new = 1 if obj.isProtected() else -1
    if old != new:
        _register_change(obj, ChangeType.protection_changed)


def _protection_changed(sender, obj, **kwargs):
    if isinstance(obj, Session):
        _register_change(obj.event_new, ChangeType.protection_changed)
    else:
        _register_change(obj, ChangeType.protection_changed)


def _acl_changed_legacy(obj, **kwargs):
    _handle_acl_change(obj)


def _acl_entry_changed(sender, obj, **kwargs):
    if not inspect(obj).persistent:
        return
    if isinstance(obj, Session):
        # if a session acl is changed we need to update all inheriting
        # contributions in that session
        for contrib in obj.contributions:
            if contrib.protection_mode == ProtectionMode.inheriting:
                _register_change(contrib, ChangeType.protection_changed)
    else:
        _register_change(obj, ChangeType.protection_changed)


def _domain_changed(obj, **kwargs):
    _register_change(obj, ChangeType.protection_changed)


def _note_changed(note, **kwargs):
    obj = note.event_new if isinstance(note.object, Session) else note.object
    _register_change(obj, ChangeType.data_changed)


def _attachment_changed(attachment_or_folder, **kwargs):
    folder = getattr(attachment_or_folder, 'folder', attachment_or_folder)
    if not isinstance(folder.object, Category):
        _register_change(folder.object.event_new, ChangeType.data_changed)


def _apply_changes(sender, **kwargs):
    if not hasattr(g, 'livesync_changes'):
        return
    for ref, changes in g.livesync_changes.iteritems():
        if is_ref_excluded(ref):
            continue
        LiveSyncQueueEntry.create(changes, ref)


def _clear_changes(sender, **kwargs):
    if not hasattr(g, 'livesync_changes'):
        return
    del g.livesync_changes


def _handle_acl_change(obj):
    if isinstance(obj, Category):
        _register_change(obj, ChangeType.protection_changed)
    elif isinstance(obj, Conference):
        if obj.getOwner():
            _register_change(obj, ChangeType.data_changed)
    elif isinstance(obj, AccessController):
        _handle_acl_change(obj.getOwner())
    else:
        raise TypeError('Unexpected object: {}'.format(type(obj).__name__))


def _register_deletion(obj):
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(ChangeType.deleted)


@unify_event_args
def _register_change(obj, action):
    if not isinstance(obj, Category):
        event = obj.event_new
        if event is None or event.is_deleted or event.as_legacy is None or event.as_legacy.getOwner() is None:
            # When deleting an event we get data change signals afterwards. We can simple ignore them.
            # When moving an event it's even worse, we get a data change notification in the middle of the move while
            # the event has no category...
            # Also, ACL changes during user merges might involve deleted objects which we also don't care about
            return
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(action)


def _init_livesync_g():
    g.setdefault('livesync_changes', defaultdict(set))
