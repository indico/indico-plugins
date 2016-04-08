"""Reference the new objects

Revision ID: 2c9618a7a2ea
Revises: 5a9176bca07d
Create Date: 2016-04-08 11:37:44.632046
"""

import sqlalchemy as sa
from alembic import op

from indico.core.db.sqlalchemy import PyIntEnum
from indico_livesync.models.queue import EntryType


# revision identifiers, used by Alembic.
revision = '2c9618a7a2ea'
down_revision = '5a9176bca07d'


def upgrade():
    op.drop_column('queues', 'type', schema='plugin_livesync')
    op.drop_column('queues', 'category_id', schema='plugin_livesync')
    op.drop_column('queues', 'event_id', schema='plugin_livesync')
    op.drop_column('queues', 'contrib_id', schema='plugin_livesync')
    op.drop_column('queues', 'subcontrib_id', schema='plugin_livesync')
    op.add_column('queues', sa.Column('category_id', sa.Integer(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('event_id', sa.Integer(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('contribution_id', sa.Integer(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('subcontribution_id', sa.Integer(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('type', PyIntEnum(EntryType), nullable=False), schema='plugin_livesync')
    op.create_index(None, 'queues', ['category_id'], schema='plugin_livesync')
    op.create_index(None, 'queues', ['event_id'], schema='plugin_livesync')
    op.create_index(None, 'queues', ['contribution_id'], schema='plugin_livesync')
    op.create_index(None, 'queues', ['subcontribution_id'], schema='plugin_livesync')
    op.create_foreign_key(None,
                          'queues', 'events',
                          ['event_id'], ['id'],
                          source_schema='plugin_livesync', referent_schema='events')
    op.create_foreign_key(None,
                          'queues', 'contributions',
                          ['contribution_id'], ['id'],
                          source_schema='plugin_livesync', referent_schema='events')
    op.create_foreign_key(None,
                          'queues', 'subcontributions',
                          ['subcontribution_id'], ['id'],
                          source_schema='plugin_livesync', referent_schema='events')
    op.create_check_constraint('valid_category_entry', 'queues',
                               'type != 1 OR (contribution_id IS NULL AND event_id IS NULL AND '
                               'subcontribution_id IS NULL AND category_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_event_entry', 'queues',
                               'type != 2 OR (category_id IS NULL AND contribution_id IS NULL AND '
                               'subcontribution_id IS NULL AND event_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_contribution_entry', 'queues',
                               'type != 3 OR (category_id IS NULL AND event_id IS NULL AND '
                               'subcontribution_id IS NULL AND contribution_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_subcontribution_entry', 'queues',
                               'type != 4 OR (category_id IS NULL AND contribution_id IS NULL AND '
                               'event_id IS NULL AND subcontribution_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_enum_change', 'queues', schema='plugin_livesync')
    op.create_check_constraint('valid_enum_change', 'queues',
                               'change IN (1, 2, 3, 4, 5)',
                               schema='plugin_livesync')


def downgrade():
    op.drop_constraint('ck_queues_valid_enum_change', 'queues', schema='plugin_livesync')
    op.create_check_constraint('valid_enum_change', 'queues',
                               'change IN (1, 2, 3, 4, 5, 6)',
                               schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')
    op.drop_column('queues', 'type', schema='plugin_livesync')
    op.drop_column('queues', 'category_id', schema='plugin_livesync')
    op.drop_column('queues', 'event_id', schema='plugin_livesync')
    op.drop_column('queues', 'subcontribution_id', schema='plugin_livesync')
    op.drop_column('queues', 'contribution_id', schema='plugin_livesync')
    op.add_column('queues', sa.Column('type', sa.String(), nullable=False), schema='plugin_livesync')
    op.add_column('queues', sa.Column('category_id', sa.String(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('event_id', sa.String(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('contrib_id', sa.String(), nullable=True), schema='plugin_livesync')
    op.add_column('queues', sa.Column('subcontrib_id', sa.String(), nullable=True), schema='plugin_livesync')
