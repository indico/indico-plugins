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

from werkzeug.datastructures import ImmutableDict

from indico.core.db.sqlalchemy import PyIntEnum, UTCDateTime, db
from indico.modules.categories.models.categories import Category
from indico.modules.events.models.events import Event
from indico.util.date_time import now_utc
from indico.util.string import format_repr, return_ascii
from indico.util.struct.enum import IndicoEnum

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.util import obj_deref


class ChangeType(int, IndicoEnum):
    created = 1
    deleted = 2
    moved = 3
    data_changed = 4
    protection_changed = 5


class EntryType(int, IndicoEnum):
    category = 1
    event = 2
    contribution = 3
    subcontribution = 4
    session = 5


_column_for_types = {
    EntryType.category: 'category_id',
    EntryType.event: 'event_id',
    EntryType.contribution: 'contribution_id',
    EntryType.subcontribution: 'subcontribution_id',
    EntryType.session: 'session_id'
}


def _make_checks():
    available_columns = set(_column_for_types.viewvalues())
    for link_type in EntryType:
        required_col = _column_for_types[link_type]
        forbidden_cols = available_columns - {required_col}
        criteria = ['{} IS NULL'.format(col) for col in sorted(forbidden_cols)]
        criteria += ['{} IS NOT NULL'.format(required_col)]
        condition = 'type != {} OR ({})'.format(link_type, ' AND '.join(criteria))
        yield db.CheckConstraint(condition, 'valid_{}_entry'.format(link_type.name))


class LiveSyncQueueEntry(db.Model):
    __tablename__ = 'queues'
    __table_args__ = tuple(_make_checks()) + ({'schema': 'plugin_livesync'},)

    #: Entry ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    #: ID of the agent this entry belongs to
    agent_id = db.Column(
        db.Integer,
        db.ForeignKey('plugin_livesync.agents.id'),
        nullable=False,
        index=True
    )

    #: Timestamp of the change
    timestamp = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )

    #: if this record has already been processed
    processed = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    #: the change type, a :class:`ChangeType`
    change = db.Column(
        PyIntEnum(ChangeType),
        nullable=False
    )

    #: The type of the changed object
    type = db.Column(
        PyIntEnum(EntryType),
        nullable=False
    )

    #: The ID of the changed category
    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.categories.id'),
        index=True,
        nullable=True
    )

    #: ID of the changed event
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.events.id'),
        index=True,
        nullable=True
    )

    #: ID of the changed contribution
    contrib_id = db.Column(
        'contribution_id',
        db.Integer,
        db.ForeignKey('events.contributions.id'),
        index=True,
        nullable=True
    )

    #: ID of the changed session
    session_id = db.Column(
        'session_id',
        db.Integer,
        db.ForeignKey('events.sessions.id'),
        index=True,
        nullable=True
    )

    #: ID of the changed subcontribution
    subcontrib_id = db.Column(
        'subcontribution_id',
        db.Integer,
        db.ForeignKey('events.subcontributions.id'),
        index=True,
        nullable=True
    )

    #: The associated :class:LiveSyncAgent
    agent = db.relationship(
        'LiveSyncAgent',
        backref=db.backref('queue', cascade='all, delete-orphan', lazy='dynamic')
    )

    category = db.relationship(
        'Category',
        lazy=True,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy=True
        )
    )

    event = db.relationship(
        'Event',
        lazy=True,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy=True
        )
    )

    session = db.relationship(
        'Session',
        lazy=False,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    contribution = db.relationship(
        'Contribution',
        lazy=False,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    subcontribution = db.relationship(
        'SubContribution',
        lazy=False,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    @property
    def object(self):
        """Return the changed object."""
        if self.type == EntryType.category:
            return self.category
        elif self.type == EntryType.event:
            return self.event
        elif self.type == EntryType.session:
            return self.session
        elif self.type == EntryType.contribution:
            return self.contribution
        elif self.type == EntryType.subcontribution:
            return self.subcontribution

    @property
    def object_ref(self):
        """Return the reference of the changed object."""
        return ImmutableDict(type=self.type, category_id=self.category_id, event_id=self.event_id,
                             session_id=self.session_id, contrib_id=self.contrib_id, subcontrib_id=self.subcontrib_id)

    @return_ascii
    def __repr__(self):
        return format_repr(self, 'id', 'agent_id', 'change', 'type',
                           category_id=None, event_id=None, session_id=None, contrib_id=None, subcontrib_id=None)

    @classmethod
    def create(cls, changes, ref, excluded_categories=set()):
        """Create a new change in all queues.

        :param changes: the change types, an iterable containing
                        :class:`ChangeType`
        :param ref: the object reference (returned by `obj_ref`)
                        of the changed object
        :param excluded_categories: set of categories (IDs) whose items
                                    will not be tracked
        """
        ref = dict(ref)
        obj = obj_deref(ref)

        if isinstance(obj, Category):
            if any(c.id in excluded_categories for c in obj.chain_query):
                return
        else:
            event = obj if isinstance(obj, Event) else obj.event
            if excluded_categories & set(event.category_chain):
                return

        for change in changes:
            for agent in LiveSyncAgent.find():
                entry = cls(agent=agent, change=change, **ref)
                db.session.add(entry)

        db.session.flush()
