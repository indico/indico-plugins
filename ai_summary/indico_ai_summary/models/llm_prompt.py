# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.db.sqlalchemy import db
from indico.util.string import format_repr


class LLMPrompt(db.Model):
    """Predefined LLM prompts"""

    __tablename__ = 'predefined_prompts'
    __table_args__ = {'schema': 'plugin_ai_summary'}

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    #: The ID of the category this prompt is defined for
    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.categories.id'),
        index=True,
        nullable=False
    )
    #: Name of the prompt
    name = db.Column(
        db.String,
        nullable=False
    )
    #: Text of the prompt
    text = db.Column(
        db.Text,
        nullable=False
    )

    #: The Category this prompt is defined for
    category = db.relationship(
        'Category',
        lazy=True,
        backref=db.backref(
            'llm_summary_prompts',
            cascade='all, delete-orphan',
            lazy='dynamic'
        )
    )

    def __repr__(self):
        return format_repr(self, 'id', 'category_id', 'name')
