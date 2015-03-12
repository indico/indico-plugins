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

from collections import defaultdict

from flask import g

from indico.core import signals
from MaKaC.accessControl import AccessController
from MaKaC.conference import ConferenceHolder, Conference, Contribution, SubContribution, Category, Session

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
    plugin.connect(signals.category.created, _created)
    plugin.connect(signals.event.created, _created)
    plugin.connect(signals.event.contribution_created, _created)
    plugin.connect(signals.event.subcontribution_created, _created)
    # deleted
    plugin.connect(signals.category.deleted, _deleted)
    plugin.connect(signals.event.deleted, _deleted)
    plugin.connect(signals.event.contribution_deleted, _deleted)
    plugin.connect(signals.event.subcontribution_deleted, _deleted)
    # title
    plugin.connect(signals.category.title_changed, _title_changed)
    plugin.connect(signals.event.data_changed, _title_changed)
    plugin.connect(signals.event.contribution_title_changed, _title_changed)
    plugin.connect(signals.event.subcontribution_title_changed, _title_changed)
    # data
    plugin.connect(signals.category.data_changed, _data_changed)
    plugin.connect(signals.event.data_changed, _data_changed)
    plugin.connect(signals.event.contribution_data_changed, _data_changed)
    plugin.connect(signals.event.subcontribution_data_changed, _data_changed)
    # protection
    plugin.connect(signals.category.protection_changed, _protection_changed)
    plugin.connect(signals.event.protection_changed, _protection_changed)
    plugin.connect(signals.event.contribution_protection_changed, _protection_changed)
    # ACLs
    plugin.connect(signals.acl.access_granted, _acl_changed)
    plugin.connect(signals.acl.access_revoked, _acl_changed)
    plugin.connect(signals.acl.modification_granted, _acl_changed)
    plugin.connect(signals.acl.modification_revoked, _acl_changed)
    # domain access
    plugin.connect(signals.category.domain_access_granted, _domain_changed)
    plugin.connect(signals.category.domain_access_revoked, _domain_changed)
    plugin.connect(signals.event.domain_access_granted, _domain_changed)
    plugin.connect(signals.event.domain_access_revoked, _domain_changed)


def _moved(obj, old_parent, new_parent, **kwargs):
    _register_change(obj, ChangeType.moved)
    category_protection = old_parent.isProtected()
    new_category_protection = new_parent.isProtected()

    if category_protection != new_category_protection and obj.getAccessProtectionLevel() == 0:
        _register_change(obj, ChangeType.protection_changed)


def _created(obj, parent, **kwargs):
    _register_change(parent, ChangeType.data_changed)
    _register_change(obj, ChangeType.created)


def _deleted(obj, **kwargs):
    parent = kwargs.pop('parent', None)
    _register_deletion(obj, parent)


def _title_changed(obj, **kwargs):
    if kwargs.pop('attr', 'title') != 'title':
        return
    _register_change(obj, ChangeType.title_changed)


def _data_changed(obj, **kwargs):
    _register_change(obj, ChangeType.data_changed)


def _protection_changed(obj, old, new, **kwargs):
    if new == 0:  # inheriting
        new = 1 if obj.isProtected() else -1
    if old != new:
        _register_change(obj, ChangeType.protection_changed)


def _acl_changed(obj, principal, **kwargs):
    _handle_acl_change(obj)


def _domain_changed(obj, **kwargs):
    _register_change(obj, ChangeType.protection_changed)


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


def _handle_acl_change(obj, child=False):
    if isinstance(obj, (Conference, Contribution, SubContribution, Category)):
        # if it was a child, emit data_changed instead
        if child:
            _register_change(obj, ChangeType.data_changed)
        else:
            _register_change(obj, ChangeType.protection_changed)
    elif isinstance(obj, Session):
        owner = obj.getOwner()
        if owner:
            _register_change(owner, ChangeType.data_changed)
    elif isinstance(obj, AccessController):
        _handle_acl_change(obj.getOwner(), child=False)
    else:
        _handle_acl_change(obj.getOwner(), child=True)


def _register_deletion(obj, parent):
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj, parent)].add(ChangeType.deleted)


def _register_change(obj, action):
    if not isinstance(obj, Category):
        event = obj.getConference()
        if event is None or ConferenceHolder().getById(event.id, True) is None or event.getOwner() is None:
            # When deleting an event we get data change signals afterwards. We can simple ignore them.
            # When moving an event it's even worse, we get a data change notification in the middle of the move while
            # the event has no category...
            # Also, ACL changes during user merges might involve deleted objects which we also don't care about
            return
    _init_livesync_g()
    g.livesync_changes[obj_ref(obj)].add(action)


def _init_livesync_g():
    if not hasattr(g, 'livesync_changes'):
        g.livesync_changes = defaultdict(set)
