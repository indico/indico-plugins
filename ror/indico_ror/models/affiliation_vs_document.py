# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2026 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from pgvector.sqlalchemy import Vector

from indico.core.db import db


class AffiliationVectorStoreDocument(db.Model):
    __tablename__ = 'affiliation_documents'
    __table_args__ = {'schema': 'plugin_ror'}

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(Vector(512), nullable=False)
    affiliation_id = db.Column(db.Integer, db.ForeignKey('indico.affiliations.id', ondelete='cascade'), nullable=True)
    affiliation = db.relationship(
        'Affiliation',
        backref=db.backref('ror_vector_store_documents', cascade='all, delete-orphan', lazy='dynamic'),
    )

    def __repr__(self):
        return f'<VectorStoreDocument(id={self.id}, content={self.content}, affiliation_id={self.affiliation_id})>'
