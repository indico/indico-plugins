# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.db.sqlalchemy import PyIntEnum, UTCDateTime, db
from indico.util.date_time import now_utc
from indico.util.enum import IndicoEnum


class EntryType(int, IndicoEnum):
    event = 1
    contribution = 2
    subcontribution = 3
    attachment = 4
    note = 5


_column_for_types = {
    EntryType.event: 'event_id',
    EntryType.contribution: 'contrib_id',
    EntryType.subcontribution: 'subcontrib_id',
    EntryType.attachment: 'attachment_id',
    EntryType.note: 'note_id'
}


def _make_checks():
    available_columns = set(_column_for_types.values())
    for link_type in EntryType:
        required_col = _column_for_types[link_type]
        forbidden_cols = available_columns - {required_col}
        criteria = [f'{required_col} IS NOT NULL']
        criteria += [f'{col} IS NULL' for col in sorted(forbidden_cols)]
        condition = 'type != {} OR ({})'.format(link_type, ' AND '.join(criteria))
        yield db.CheckConstraint(condition, f'valid_{link_type.name}_entry')


class CitadelSearchAppIdMap(db.Model):
    __tablename__ = 'es_id_map'
    __table_args__ = tuple(_make_checks()) + ({'schema': 'plugin_citadel'},)

    #: Entry ID
    id = db.Column(
        db.Integer,
        autoincrement=True,
        primary_key=True
    )

    #: ID of the document in the backend this entry belongs to
    search_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )

    timestamp = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )

    #: The type of the search entry object
    entry_type = db.Column(
        PyIntEnum(EntryType),
        nullable=False
    )

    #: ID of the search entry event
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.events.id'),
        index=True,
        nullable=True
    )

    #: ID of the search entry contribution
    contrib_id = db.Column(
        db.Integer,
        db.ForeignKey('events.contributions.id'),
        index=True,
        nullable=True
    )

    #: ID of the search entry subcontribution
    subcontrib_id = db.Column(
        db.Integer,
        db.ForeignKey('events.subcontributions.id'),
        index=True,
        nullable=True
    )

    #: ID of the search entry attachment
    attachment_id = db.Column(
        db.Integer,
        db.ForeignKey('attachments.attachments.id'),
        index=True,
        nullable=True
    )

    #: ID of the search entry note
    note_id = db.Column(
        db.Integer,
        db.ForeignKey('events.notes.id'),
        index=True,
        nullable=True
    )

    event = db.relationship(
        'Event',
        lazy=True,
        backref=db.backref(
            'citadel_es_entries',
            cascade='all, delete-orphan',
            lazy=True
        )
    )

    contribution = db.relationship(
        'Contribution',
        lazy=False,
        backref=db.backref(
            'citadel_es_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    subcontribution = db.relationship(
        'SubContribution',
        lazy=False,
        backref=db.backref(
            'citadel_es_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    attachment = db.relationship(
        'Attachment',
        lazy=False,
        backref=db.backref(
            'citadel_es_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    note = db.relationship(
        'EventNote',
        lazy=False,
        backref=db.backref(
            'citadel_es_entries',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    @classmethod
    def get_search_id(cls, oid, obj_type):
        """Get the search_id for a given object type and id.

        :param oid: The id of the object
        :param obj_type: the EntryType of the object
        """

        obj = cls.query.filter_by(entry_type=obj_type)
        if obj_type == EntryType.event:
            obj = obj.filter_by(event_id=oid)
        elif obj_type == EntryType.contribution:
            obj = obj.filter_by(contrib_id=oid)
        elif obj_type == EntryType.subcontribution:
            obj = obj.filter_by(subcontrib_id=oid)
        elif obj_type == EntryType.attachment:
            obj = obj.filter_by(attachment_id=oid)
        elif obj_type == EntryType.note:
            obj = obj.filter_by(note_id=oid)

        obj = obj.first()
        return obj.search_id if obj else None

    @classmethod
    def create(cls, eid, oid, obj_type):
        """Create a new mapping.

        :param eid: The search_id to map the oid to
        :param oid: The id of the object
        :param obj_type: the EntryType of the object
        """
        if obj_type == EntryType.event:
            entry = cls(search_id=eid, entry_type=obj_type, event_id=oid)
        elif obj_type == EntryType.contribution:
            entry = cls(search_id=eid, entry_type=obj_type, contrib_id=oid)
        elif obj_type == EntryType.subcontribution:
            entry = cls(search_id=eid, entry_type=obj_type, subcontrib_id=oid)
        elif obj_type == EntryType.attachment:
            entry = cls(search_id=eid, entry_type=obj_type, attachment_id=oid)
        elif obj_type == EntryType.note:
            entry = cls(search_id=eid, entry_type=obj_type, note_id=oid)
        else:
            raise Exception(f'Unsupported object type {obj_type}')

        db.session.add(entry)