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

from werkzeug.datastructures import ImmutableDict

from indico.core.db.sqlalchemy import db, UTCDateTime, PyIntEnum
from indico.util.date_time import now_utc
from indico.util.string import return_ascii, format_repr
from indico.util.struct.enum import IndicoEnum
from MaKaC.conference import CategoryManager

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.util import obj_deref


class ChangeType(int, IndicoEnum):
    created = 1
    deleted = 2
    moved = 3
    data_changed = 4
    title_changed = 5
    protection_changed = 6


class EntryType(int, IndicoEnum):
    category = 1
    event = 2
    contribution = 3
    subcontribution = 4


_column_for_types = {
    EntryType.category: 'category_id',
    EntryType.event: 'event_id',
    EntryType.contribution: 'contribution_id',
    EntryType.subcontribution: 'subcontribution_id'
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
        index=True,
        nullable=True
    )

    #: The event ID of the changed event/contribution/subcontribution
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.events.id'),
        index=True,
        nullable=True
    )

    #: The contribution ID of the changed contribution/subcontribution
    contrib_id = db.Column(
        'contribution_id',
        db.Integer,
        db.ForeignKey('events.contributions.id'),
        index=True,
        nullable=True
    )

    #: The subcontribution ID of the changed subcontribution
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

    event = db.relationship(
        'Event',
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
    def category(self):
        return CategoryManager().getById(str(self.category_id), True)

    @category.setter
    def category(self, value):
        self.category_id = int(value.id) if value is not None else None

    @property
    def object(self):
        """Returns the changed object"""
        return obj_deref(self.object_ref)

    @property
    def object_ref(self):
        """Returns the reference of the changed object"""
        return ImmutableDict(type=self.type.name, category_id=self.category_id, event_id=self.event_id,
                             contrib_id=self.contrib_id, subcontrib_id=self.subcontrib_id)

    @return_ascii
    def __repr__(self):
        ref_repr = '{}.{}.{}.{}'.format(self.category_id if self.category_id else 'x',
                                        self.event_id if self.event_id else 'x',
                                        self.contrib_id if self.contrib_id else 'x',
                                        self.subcontrib_id if self.subcontrib_id else 'x')
        return format_repr(self, 'agent', 'id', 'type', 'change', _text=ref_repr)

    @classmethod
    def create(cls, changes, obj_ref):
        """Creates a new change in all queues

        :param changes: the change types, an iterable containing
                        :class:`ChangeType`
        :param obj_ref: the object reference (returned by `obj_ref`)
                        of the changed object
        """
        obj_ref = dict(obj_ref)
        for agent in LiveSyncAgent.find():
            for change in changes:
                entry = cls(agent=agent, change=change, **obj_ref)
                db.session.add(entry)
        db.session.flush()

    def iter_subentries(self):
        """Iterates through all children

        The only field of the yielded items that should be used are
        `type`, `object` and `object_ref`.
        """
        if self.type not in {'category', 'event', 'contribution'}:
            return
        data = {'change': self.change,
                'category_id': self.category_id, 'event_id': self.event_id,
                'contrib_id': self.contrib_id, 'subcontrib_id': self.subcontrib_id}
        if self.type == 'category':
            for event in self.object.iterAllConferences():
                new_data = dict(data)
                new_data['type'] = 'event'
                new_data['event_id'] = event.getId()
                yield LiveSyncQueueEntry(**new_data)
        elif self.type == 'event':
            for contrib in self.object.iterContributions():
                new_data = dict(data)
                new_data['type'] = 'contribution'
                new_data['contrib_id'] = contrib.getId()
                yield LiveSyncQueueEntry(**new_data)
        elif self.type == 'contribution':
            for subcontrib in self.object.iterSubContributions():
                new_data = dict(data)
                new_data['type'] = 'subcontribution'
                new_data['subcontrib_id'] = subcontrib.getId()
                yield LiveSyncQueueEntry(**new_data)
