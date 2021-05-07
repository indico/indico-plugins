"""Add mapping table

Revision ID: 0cf18be7ade1
Revises:
Create Date: 2021-03-30 17:42:59.493830
"""

from enum import Enum

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.ddl import CreateSchema, DropSchema

from indico.core.db.sqlalchemy import PyIntEnum


# revision identifiers, used by Alembic.
revision = '0cf18be7ade1'
down_revision = None
branch_labels = None
depends_on = None


class _EntryType(int, Enum):
    event = 1
    contribution = 2
    subcontribution = 3
    attachment = 4
    note = 5


def upgrade():
    op.execute(CreateSchema('plugin_citadel'))
    op.create_table(
        'id_map',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('citadel_id', sa.Integer(), nullable=False, index=True, unique=True),
        sa.Column('entry_type', PyIntEnum(_EntryType), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True, index=True, unique=True),
        sa.Column('contrib_id', sa.Integer(), nullable=True, index=True, unique=True),
        sa.Column('subcontrib_id', sa.Integer(), nullable=True, index=True, unique=True),
        sa.Column('attachment_id', sa.Integer(), nullable=True, index=True, unique=True),
        sa.Column('note_id', sa.Integer(), nullable=True, index=True, unique=True),
        sa.Column('attachment_file_id', sa.Integer(), nullable=True, index=True, unique=True),
        sa.CheckConstraint('entry_type != 1 OR (event_id IS NOT NULL AND attachment_id IS NULL AND contrib_id IS NULL AND note_id IS NULL AND subcontrib_id IS NULL)', name='valid_event_entry'),
        sa.CheckConstraint('entry_type != 2 OR (contrib_id IS NOT NULL AND attachment_id IS NULL AND event_id IS NULL AND note_id IS NULL AND subcontrib_id IS NULL)', name='valid_contribution_entry'),
        sa.CheckConstraint('entry_type != 3 OR (subcontrib_id IS NOT NULL AND attachment_id IS NULL AND contrib_id IS NULL AND event_id IS NULL AND note_id IS NULL)', name='valid_subcontribution_entry'),
        sa.CheckConstraint('entry_type != 4 OR (attachment_id IS NOT NULL AND contrib_id IS NULL AND event_id IS NULL AND note_id IS NULL AND subcontrib_id IS NULL)', name='valid_attachment_entry'),
        sa.CheckConstraint('entry_type != 5 OR (note_id IS NOT NULL AND attachment_id IS NULL AND contrib_id IS NULL AND event_id IS NULL AND subcontrib_id IS NULL)', name='valid_note_entry'),
        sa.ForeignKeyConstraint(['attachment_id'], ['attachments.attachments.id']),
        sa.ForeignKeyConstraint(['contrib_id'], ['events.contributions.id']),
        sa.ForeignKeyConstraint(['event_id'], ['events.events.id']),
        sa.ForeignKeyConstraint(['note_id'], ['events.notes.id']),
        sa.ForeignKeyConstraint(['subcontrib_id'], ['events.subcontributions.id']),
        sa.ForeignKeyConstraint(['attachment_file_id'], ['attachments.files.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='plugin_citadel'
    )


def downgrade():
    op.drop_table('id_map', schema='plugin_citadel')
    op.execute(DropSchema('plugin_citadel'))
