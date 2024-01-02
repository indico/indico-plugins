# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.db import db
from indico.core.db.sqlalchemy import PyIntEnum
from indico.modules.attachments import Attachment
from indico.modules.events import Event
from indico.modules.events.contributions import Contribution
from indico.modules.events.contributions.models.subcontributions import SubContribution
from indico.modules.events.notes.models.notes import EventNote
from indico.util.enum import IndicoIntEnum
from indico.util.string import format_repr


class EntryType(IndicoIntEnum):
    event = 1
    contribution = 2
    subcontribution = 3
    attachment = 4
    note = 5


_types_for_model = {
    Event: EntryType.event,
    Contribution: EntryType.contribution,
    SubContribution: EntryType.subcontribution,
    Attachment: EntryType.attachment,
    EventNote: EntryType.note,
}

_column_for_types = {
    EntryType.event: 'event_id',
    EntryType.contribution: 'contrib_id',
    EntryType.subcontribution: 'subcontrib_id',
    EntryType.attachment: 'attachment_id',
    EntryType.note: 'note_id'
}


def get_entry_type(entry):
    for model, entry_type in _types_for_model.items():
        if isinstance(entry, model):
            return entry_type


def _make_checks():
    available_columns = set(_column_for_types.values())
    for link_type in EntryType:
        required_col = _column_for_types[link_type]
        forbidden_cols = available_columns - {required_col}
        criteria = [f'{required_col} IS NOT NULL']
        criteria += [f'{col} IS NULL' for col in sorted(forbidden_cols)]
        condition = 'entry_type != {} OR ({})'.format(link_type, ' AND '.join(criteria))
        yield db.CheckConstraint(condition, f'valid_{link_type.name}_entry')


class CitadelIdMap(db.Model):
    __tablename__ = 'id_map'
    __table_args__ = (*_make_checks(), {'schema': 'plugin_citadel'})

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    citadel_id = db.Column(
        db.Integer,
        nullable=False,
        index=True,
        unique=True
    )
    entry_type = db.Column(
        PyIntEnum(EntryType),
        nullable=False
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.events.id'),
        index=True,
        nullable=True,
        unique=True
    )
    contrib_id = db.Column(
        db.Integer,
        db.ForeignKey('events.contributions.id'),
        index=True,
        nullable=True,
        unique=True
    )
    subcontrib_id = db.Column(
        db.Integer,
        db.ForeignKey('events.subcontributions.id'),
        index=True,
        nullable=True,
        unique=True
    )
    attachment_id = db.Column(
        db.Integer,
        db.ForeignKey('attachments.attachments.id'),
        index=True,
        nullable=True,
        unique=True
    )
    note_id = db.Column(
        db.Integer,
        db.ForeignKey('events.notes.id'),
        index=True,
        nullable=True,
        unique=True
    )
    attachment_file_id = db.Column(
        db.Integer,
        db.ForeignKey('attachments.files.id'),
        index=True,
        nullable=True,
        unique=True
    )

    event = db.relationship(
        'Event',
        lazy=True,
        backref=db.backref(
            'citadel_id_mapping',
            uselist=False,
            lazy=True
        )
    )
    contribution = db.relationship(
        'Contribution',
        lazy=True,
        backref=db.backref(
            'citadel_id_mapping',
            uselist=False,
            lazy=True
        )
    )
    subcontribution = db.relationship(
        'SubContribution',
        lazy=True,
        backref=db.backref(
            'citadel_id_mapping',
            uselist=False,
            lazy=True
        )
    )
    attachment = db.relationship(
        'Attachment',
        lazy=True,
        backref=db.backref(
            'citadel_id_mapping',
            uselist=False,
            lazy=True
        )
    )
    note = db.relationship(
        'EventNote',
        lazy=True,
        backref=db.backref(
            'citadel_id_mapping',
            uselist=False,
            lazy=True
        )
    )
    attachment_file = db.relationship(
        'AttachmentFile',
        lazy=True,
        backref=db.backref(
            'citadel_id_mapping',
            uselist=False,
            lazy=True
        )
    )

    def __repr__(self):
        return format_repr(self, 'id', 'entry_type', event_id=None, contrib_id=None, subcontrib_id=None,
                           attachment_id=None, note_id=None, attachment_file_id=None, _repr=self.citadel_id)

    @classmethod
    def get_citadel_id(cls, obj_type, obj_id):
        """Get the citadel_id for a given object type and id.

        :param obj_type: The EntryType of the object
        :param obj_id: The id of the object
        """
        query = db.session.query(cls.citadel_id).filter_by(entry_type=obj_type)
        attr = _column_for_types.get(obj_type)
        if not attr:
            raise Exception(f'Unsupported object type {obj_type}')
        return query.filter(getattr(cls, attr) == obj_id).scalar()

    @classmethod
    def create(cls, obj_type, obj_id, citadel_id):
        """Create a new mapping.

        :param obj_type: The EntryType of the object
        :param obj_id: The id of the object
        :param citadel_id: The citadel entry ID
        """
        attr = _column_for_types.get(obj_type)
        if not attr:
            raise Exception(f'Unsupported object type {obj_type}')
        entry = cls(citadel_id=citadel_id, entry_type=obj_type, **{attr: obj_id})
        db.session.add(entry)
