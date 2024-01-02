# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from collections import defaultdict

from flask import g
from sqlalchemy import inspect

from indico.core import signals
from indico.core.db.sqlalchemy.links import LinkType
from indico.core.db.sqlalchemy.protection import ProtectionMode
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.attachments.models.folders import AttachmentFolder
from indico.modules.categories.models.categories import Category
from indico.modules.events import Event
from indico.modules.events.contributions.models.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.modules.events.sessions import Session
from indico.modules.events.sessions.models.blocks import SessionBlock
from indico.modules.events.timetable.models.entries import TimetableEntryType

from indico_livesync.models.queue import ChangeType, LiveSyncQueueEntry
from indico_livesync.util import get_excluded_categories, obj_ref


def connect_signals(plugin):
    # request
    plugin.connect(signals.core.after_process, _apply_changes)
    # moved
    plugin.connect(signals.category.moved, _moved)
    plugin.connect(signals.event.moved, _moved)
    # created
    plugin.connect(signals.event.created, _created)
    plugin.connect(signals.event.restored, _restored)
    plugin.connect(signals.event.contribution_created, _created)
    plugin.connect(signals.event.subcontribution_created, _created)
    # deleted
    plugin.connect(signals.event.deleted, _deleted)
    plugin.connect(signals.event.contribution_deleted, _deleted)
    plugin.connect(signals.event.subcontribution_deleted, _deleted)
    # updated
    plugin.connect(signals.event.updated, _updated)
    plugin.connect(signals.event.contribution_updated, _updated)
    plugin.connect(signals.event.subcontribution_updated, _updated)
    # event times
    plugin.connect(signals.event.times_changed, _event_times_changed, sender=Event)
    plugin.connect(signals.event.times_changed, _event_times_changed, sender=Contribution)
    # location
    plugin.connect(signals.event.location_changed, _location_changed, sender=Event)
    plugin.connect(signals.event.location_changed, _location_changed, sender=Contribution)
    plugin.connect(signals.event.location_changed, _location_changed, sender=Session)
    plugin.connect(signals.event.location_changed, _session_block_location_changed, sender=SessionBlock)
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
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Category)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Event)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Session)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Contribution)
    # notes
    plugin.connect(signals.event.notes.note_added, _created)
    plugin.connect(signals.event.notes.note_restored, _restored)
    plugin.connect(signals.event.notes.note_deleted, _deleted)
    plugin.connect(signals.event.notes.note_modified, _updated)
    # attachments
    plugin.connect(signals.attachments.folder_deleted, _attachment_folder_deleted)
    plugin.connect(signals.attachments.attachment_created, _created)
    plugin.connect(signals.attachments.attachment_deleted, _attachment_deleted)
    plugin.connect(signals.attachments.attachment_updated, _updated)
    plugin.connect(signals.acl.protection_changed, _attachment_folder_protection_changed, sender=AttachmentFolder)
    plugin.connect(signals.acl.protection_changed, _protection_changed, sender=Attachment)
    plugin.connect(signals.acl.entry_changed, _attachment_folder_acl_entry_changed, sender=AttachmentFolder)
    plugin.connect(signals.acl.entry_changed, _acl_entry_changed, sender=Attachment)


def _is_category_excluded(category):
    excluded_categories = get_excluded_categories()
    return any(c.id in excluded_categories for c in category.chain_query)


def _moved(obj, old_parent, **kwargs):
    # if an unlisted event is moved, it triggers a creation instead
    if isinstance(obj, Event) and old_parent is None:
        _register_change(obj, ChangeType.created)
    else:
        _register_change(obj, ChangeType.moved)

        new_category = obj if isinstance(obj, Category) else obj.category
        old_excluded = _is_category_excluded(old_parent) if old_parent else False
        new_excluded = _is_category_excluded(new_category)
        if old_excluded != new_excluded:
            _register_change(obj, ChangeType.unpublished if new_excluded else ChangeType.published)

    if obj.is_inheriting:
        # If protection is inherited, check whether it changed
        category_protection = old_parent.effective_protection_mode if old_parent else None
        new_category_protection = obj.protection_parent.effective_protection_mode
        # Protection of new parent is different
        if category_protection != new_category_protection:
            _register_change(obj, ChangeType.protection_changed)


def _created(obj, **kwargs):
    if not isinstance(obj, (Event, EventNote, Attachment, Contribution, SubContribution)):
        raise TypeError(f'Unexpected object: {type(obj).__name__}')
    _register_change(obj, ChangeType.created)


def _restored(obj, **kwargs):
    _register_change(obj, ChangeType.undeleted)


def _deleted(obj, **kwargs):
    _register_deletion(obj)


def _updated(obj, **kwargs):
    _register_change(obj, ChangeType.data_changed)


def _event_times_changed(sender, obj, **kwargs):
    _register_change(obj, ChangeType.data_changed)


def _session_block_location_changed(sender, obj, **kwargs):
    for contrib in obj.contributions:
        _register_change(contrib, ChangeType.location_changed)


def _location_changed(sender, obj, **kwargs):
    _register_change(obj, ChangeType.location_changed)


def _timetable_changed(entry, **kwargs):
    if entry.type == TimetableEntryType.CONTRIBUTION:
        _register_change(entry.object, ChangeType.data_changed)


def _category_protection_changed(sender, obj, mode, old_mode, **kwargs):
    parent_mode = obj.protection_parent.effective_protection_mode if obj.protection_parent else None
    if ((old_mode == ProtectionMode.inheriting and parent_mode == mode) or
            (old_mode == parent_mode and mode == ProtectionMode.inheriting)):
        return
    _protection_changed(sender, obj, mode=mode, old_mode=old_mode, **kwargs)


def _protection_changed(sender, obj, **kwargs):
    if not inspect(obj).persistent:
        return
    _register_change(obj, ChangeType.protection_changed)


def _acl_entry_changed(sender, obj, entry, old_data, **kwargs):
    if not inspect(obj).persistent:
        return
    register = False
    # entry deleted
    if entry is None and old_data is not None:
        register = True
    # entry added
    elif entry is not None and old_data is None:
        register = True
    # entry updated
    elif entry is not None and old_data is not None:
        old_access = bool(old_data['read_access'] or old_data['full_access'] or old_data['permissions'])
        new_access = bool(entry.full_access or entry.read_access or entry.permissions)
        register = old_access != new_access
    if register:
        _register_change(obj, ChangeType.protection_changed)


def _attachment_folder_deleted(folder, **kwargs):
    if folder.link_type not in (LinkType.event, LinkType.contribution, LinkType.subcontribution):
        return
    for attachment in folder.attachments:
        _register_deletion(attachment)


def _attachment_deleted(attachment, **kwargs):
    if attachment.folder.link_type not in (LinkType.event, LinkType.contribution, LinkType.subcontribution):
        return
    _register_deletion(attachment)


def _attachment_folder_protection_changed(sender, obj, **kwargs):
    if not inspect(obj).persistent:
        return
    if obj.link_type not in (LinkType.event, LinkType.contribution, LinkType.subcontribution):
        return
    for attachment in obj.attachments:
        _register_change(attachment, ChangeType.protection_changed)


def _attachment_folder_acl_entry_changed(sender, obj, entry, old_data, **kwargs):
    if not inspect(obj).persistent:
        return
    if obj.link_type not in (LinkType.event, LinkType.contribution, LinkType.subcontribution):
        return
    for attachment in obj.attachments:
        _acl_entry_changed(type(attachment), attachment, entry, old_data)


def _apply_changes(sender, **kwargs):
    if not hasattr(g, 'livesync_changes'):
        return
    excluded_categories = get_excluded_categories()
    for ref, changes in g.livesync_changes.items():
        LiveSyncQueueEntry.create(changes, ref, excluded_categories=excluded_categories)


def _register_deletion(obj):
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(ChangeType.deleted)


def _register_change(obj, action):
    if not isinstance(obj, Category):
        event = obj.folder.event if isinstance(obj, Attachment) else obj.event
        if event is None or event.is_deleted:
            # When deleting an event we get data change signals afterwards. We can simple ignore them.
            # Also, ACL changes during user merges might involve deleted objects which we also don't care about
            return
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(action)


def _init_livesync_g():
    g.setdefault('livesync_changes', defaultdict(set))
