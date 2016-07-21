"""Add session to LiveSyncQueueEntry

Revision ID: 205f944640f6
Revises: 230c086da074
Create Date: 2016-07-15 17:36:12.702497
"""

import sqlalchemy as sa
from alembic import op


revision = '205f944640f6'
down_revision = '230c086da074'


def upgrade():
    op.add_column('queues', sa.Column('session_id', sa.Integer(), nullable=True), schema='plugin_livesync')
    op.create_foreign_key(None,
                          'queues', 'sessions',
                          ['session_id'], ['id'],
                          source_schema='plugin_livesync', referent_schema='events')
    op.create_index(None, 'queues', ['session_id'], unique=False, schema='plugin_livesync')

    op.drop_constraint('ck_queues_valid_enum_type', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')

    op.create_check_constraint('valid_enum_type', 'queues',
                               'type IN (1, 2, 3, 4, 5)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_category_entry', 'queues',
                               'type != 1 OR (contribution_id IS NULL AND event_id IS NULL AND session_id IS NULL AND '
                               'subcontribution_id IS NULL AND category_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_event_entry', 'queues',
                               'type != 2 OR (category_id IS NULL AND contribution_id IS NULL AND session_id IS NULL '
                               'AND subcontribution_id IS NULL AND event_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_session_entry', 'queues',
                               'type != 5 OR (category_id IS NULL AND event_id IS NULL AND contribution_id IS NULL '
                               'AND subcontribution_id IS NULL AND session_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_contribution_entry', 'queues',
                               'type != 3 OR (category_id IS NULL AND event_id IS NULL AND session_id IS NULL AND '
                               'subcontribution_id IS NULL AND contribution_id IS NOT NULL)',
                               schema='plugin_livesync')
    op.create_check_constraint('valid_subcontribution_entry', 'queues',
                               'type != 4 OR (category_id IS NULL AND contribution_id IS NULL AND session_id IS NULL '
                               'AND event_id IS NULL AND subcontribution_id IS NOT NULL)',
                               schema='plugin_livesync')


def downgrade():
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_session_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')

    op.drop_column('queues', 'session_id', schema='plugin_livesync')

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

    op.drop_constraint('ck_queues_valid_enum_type', 'queues', schema='plugin_livesync')
    op.create_check_constraint('valid_enum_type', 'queues',
                               'type IN (1, 2, 3, 4)',
                               schema='plugin_livesync')
