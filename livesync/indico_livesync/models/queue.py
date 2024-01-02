# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import g

from indico.core.db.sqlalchemy import PyIntEnum, UTCDateTime, db
from indico.modules.attachments.models.attachments import Attachment
from indico.modules.categories.models.categories import Category
from indico.util.date_time import now_utc
from indico.util.enum import IndicoIntEnum
from indico.util.string import format_repr

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.util import obj_deref


class ChangeType(IndicoIntEnum):
    created = 1
    deleted = 2
    moved = 3
    data_changed = 4
    protection_changed = 5
    location_changed = 6
    undeleted = 7
    published = 8
    unpublished = 9


class EntryType(IndicoIntEnum):
    category = 1
    event = 2
    contribution = 3
    subcontribution = 4
    session = 5
    note = 6
    attachment = 7


_column_for_types = {
    EntryType.category: 'category_id',
    EntryType.event: 'event_id',
    EntryType.contribution: 'contribution_id',
    EntryType.subcontribution: 'subcontribution_id',
    EntryType.session: 'session_id',
    EntryType.note: 'note_id',
    EntryType.attachment: 'attachment_id',
}


def _make_checks():
    available_columns = set(_column_for_types.values())
    for link_type in EntryType:
        required_col = _column_for_types[link_type]
        forbidden_cols = available_columns - {required_col}
        criteria = [f'{col} IS NULL' for col in sorted(forbidden_cols)]
        criteria += [f'{required_col} IS NOT NULL']
        condition = 'type != {} OR ({})'.format(link_type, ' AND '.join(criteria))
        yield db.CheckConstraint(condition, f'valid_{link_type.name}_entry')


class LiveSyncQueueEntry(db.Model):
    __tablename__ = 'queues'
    __table_args__ = (*_make_checks(), {'schema': 'plugin_livesync'})

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

    #: ID of the changed note
    note_id = db.Column(
        'note_id',
        db.Integer,
        db.ForeignKey('events.notes.id'),
        index=True,
        nullable=True
    )

    #: ID of the changed attachment
    attachment_id = db.Column(
        'attachment_id',
        db.Integer,
        db.ForeignKey('attachments.attachments.id'),
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
            lazy='dynamic'
        )
    )

    event = db.relationship(
        'Event',
        lazy=True,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
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

    note = db.relationship(
        'EventNote',
        lazy=False,
        backref=db.backref(
            'livesync_queue_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    attachment = db.relationship(
        'Attachment',
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
        elif self.type == EntryType.note:
            return self.note
        elif self.type == EntryType.attachment:
            return self.attachment

    def __repr__(self):
        return format_repr(self, 'id', 'agent_id', 'change', 'type',
                           category_id=None, event_id=None, session_id=None, contrib_id=None, subcontrib_id=None,
                           note_id=None, attachment_id=None)

    @classmethod
    def create(cls, changes, ref, excluded_categories=None):
        """Create a new change in all queues.

        :param changes: the change types, an iterable containing
                        :class:`ChangeType`
        :param ref: the object reference (returned by `obj_ref`)
                        of the changed object
        :param excluded_categories: set of categories (IDs) whose items
                                    will not be tracked
        """
        if excluded_categories is None:
            excluded_categories = set()

        ref = dict(ref)
        obj = obj_deref(ref)

        if ChangeType.published not in changes and ChangeType.unpublished not in changes:
            if isinstance(obj, Category):
                if any(c.id in excluded_categories for c in obj.chain_query):
                    return
            else:
                event = obj.folder.event if isinstance(obj, Attachment) else obj.event
                if event.is_unlisted:
                    return
                if event.category not in g.setdefault('livesync_excluded_categories_checked', {}):
                    g.livesync_excluded_categories_checked[event.category] = \
                        excluded_categories & set(event.category_chain)
                if g.livesync_excluded_categories_checked[event.category]:
                    return

        try:
            agents = g.livesync_agents
        except AttributeError:
            agents = g.livesync_agents = LiveSyncAgent.query.all()

        for change in changes:
            for agent in agents:
                entry = cls(agent=agent, change=change, **ref)
                db.session.add(entry)

        db.session.flush()
