# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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
from MaKaC.conference import Conference, Contribution, SubContribution, Category, Session

from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType
from indico_livesync.util import obj_ref


class LiveSyncSignalHandler(object):
    def __init__(self, plugin):
        # request
        plugin.connect(signals.after_process, self._apply_changes)
        plugin.connect(signals.before_retry, self._clear_changes)
        # moved
        plugin.connect(signals.category_moved, self._moved)
        plugin.connect(signals.event_moved, self._moved)
        # created
        plugin.connect(signals.category_created, self._created)
        plugin.connect(signals.event_created, self._created)
        plugin.connect(signals.contribution_created, self._created)
        plugin.connect(signals.subcontribution_created, self._created)
        # deleted
        plugin.connect(signals.category_deleted, self._deleted)
        plugin.connect(signals.event_deleted, self._deleted)
        plugin.connect(signals.contribution_deleted, self._deleted)
        plugin.connect(signals.subcontribution_deleted, self._deleted)
        # title
        plugin.connect(signals.category_title_changed, self._title_changed)
        plugin.connect(signals.event_data_changed, self._title_changed)
        plugin.connect(signals.contribution_title_changed, self._title_changed)
        plugin.connect(signals.subcontribution_title_changed, self._title_changed)
        # data
        plugin.connect(signals.category_data_changed, self._data_changed)
        plugin.connect(signals.event_data_changed, self._data_changed)
        plugin.connect(signals.contribution_data_changed, self._data_changed)
        plugin.connect(signals.subcontribution_data_changed, self._data_changed)
        # protection
        plugin.connect(signals.category_protection_changed, self._protection_changed)
        plugin.connect(signals.event_protection_changed, self._protection_changed)
        plugin.connect(signals.contribution_protection_changed, self._protection_changed)
        # ACLs
        plugin.connect(signals.access_granted, self._acl_changed)
        plugin.connect(signals.access_revoked, self._acl_changed)
        plugin.connect(signals.modification_granted, self._acl_changed)
        plugin.connect(signals.modification_revoked, self._acl_changed)
        # domain access
        plugin.connect(signals.category_domain_access_granted, self._domain_changed)
        plugin.connect(signals.category_domain_access_revoked, self._domain_changed)
        plugin.connect(signals.event_domain_access_granted, self._domain_changed)
        plugin.connect(signals.event_domain_access_revoked, self._domain_changed)

    def _moved(self, obj, old_parent, new_parent, **kwargs):
        print '_moved', obj, old_parent, new_parent
        self.register_change(obj, 'moved')
        category_protection = old_parent.isProtected()
        new_category_protection = new_parent.isProtected()

        if category_protection != new_category_protection and obj.getAccessProtectionLevel() == 0:
            self.register_change(obj, ChangeType.protection_changed)

    def _created(self, obj, parent, **kwargs):
        print '_created', obj, parent
        self.register_change(parent, ChangeType.data_changed)
        self.register_change(obj, ChangeType.created)

    def _deleted(self, obj, **kwargs):
        print '_deleted', obj, kwargs
        parent = kwargs.pop('parent', None)
        self.register_deletion(obj, parent)

    def _title_changed(self, obj, **kwargs):
        if kwargs.pop('attr', 'title') != 'title':
            return
        print '_title_changed', obj, kwargs
        self.register_change(obj, ChangeType.title_changed)

    def _data_changed(self, obj, **kwargs):
        print '_data_changed', obj, kwargs
        self.register_change(obj, ChangeType.data_changed)

    def _protection_changed(self, obj, old, new, **kwargs):
        print '_protection_changed', obj, old, new
        if new == 0:  # inheriting
            new = 1 if obj.isProtected() else -1
        if old != new:
            self.register_change(obj, ChangeType.protection_changed)

    def _acl_changed(self, obj, principal, **kwargs):
        print '_acl_changed', obj, principal
        self._handle_acl_change(obj)

    def _handle_acl_change(self, obj, child=False):
        if isinstance(obj, (Conference, Contribution, SubContribution, Category)):
            # if it was a child, emit data_changed instead
            if child:
                self.register_change(obj, ChangeType.data_changed)
            else:
                self.register_change(obj, ChangeType.protection_changed)
        elif isinstance(obj, Session):
            owner = obj.getOwner()
            if owner:
                self.register_change(owner, ChangeType.data_changed)
        elif isinstance(obj, AccessController):
            self._handle_acl_change(obj.getOwner(), child=False)
        else:
            self._handle_acl_change(obj.getOwner(), child=True)

    def _domain_changed(self, obj, **kwargs):
        print '_domain_changed', obj
        self.register_change(obj, ChangeType.protection_changed)

    def register_deletion(self, obj, parent):
        self.init_livesync_g()
        g.livesync[obj_ref(obj, parent)].add(ChangeType.deleted)

    def register_change(self, obj, action):
        self.init_livesync_g()
        g.livesync[obj_ref(obj)].add(action)

    def init_livesync_g(self):
        if not hasattr(g, 'livesync'):
            g.livesync = defaultdict(set)

    def _apply_changes(self, sender, **kwargs):
        if not hasattr(g, 'livesync'):
            return
        for ref, changes in g.livesync.iteritems():
            LiveSyncQueueEntry.create(changes, ref)

    def _clear_changes(self, sender, **kwargs):
        if not hasattr(g, 'livesync'):
            return
        del g.livesync
