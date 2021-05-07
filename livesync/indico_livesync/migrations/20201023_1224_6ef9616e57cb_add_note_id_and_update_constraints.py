"""Add note_id and update constraints

Revision ID: 6ef9616e57cb
Revises: aa0dbc6c14aa
Create Date: 2020-10-23 12:24:51.648130
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '6ef9616e57cb'
down_revision = 'aa0dbc6c14aa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('queues', sa.Column('note_id', sa.Integer(), nullable=True, index=True), schema='plugin_livesync')
    op.create_foreign_key(None, 'queues', 'notes', ['note_id'], ['id'], source_schema='plugin_livesync',
                          referent_schema='events')
    op.drop_constraint('ck_queues_valid_enum_type', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_session_entry', 'queues', schema='plugin_livesync')
    op.execute('''
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_enum_type CHECK ((type = ANY (ARRAY[1, 2, 3, 4, 5, 6])));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_category_entry CHECK (((type <> 1) OR ((contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (category_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_event_entry CHECK (((type <> 2) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (event_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_contribution_entry CHECK (((type <> 3) OR ((category_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (contribution_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_subcontribution_entry CHECK (((type <> 4) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_session_entry CHECK (((type <> 5) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (subcontribution_id IS NULL) AND (session_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_note_entry CHECK (((type <> 6) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (note_id IS NOT NULL))));
    ''')


def downgrade():
    op.execute('DELETE FROM plugin_livesync.queues WHERE type = 6')

    op.drop_constraint('ck_queues_valid_enum_type', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_session_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_note_entry', 'queues', schema='plugin_livesync')

    op.drop_column('queues', 'note_id', schema='plugin_livesync')

    op.execute('''
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_enum_type CHECK ((type = ANY (ARRAY[1, 2, 3, 4, 5])));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_category_entry CHECK (((type <> 1) OR ((contribution_id IS NULL) AND (event_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (category_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_event_entry CHECK (((type <> 2) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (event_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_contribution_entry CHECK (((type <> 3) OR ((category_id IS NULL) AND (event_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (contribution_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_subcontribution_entry CHECK (((type <> 4) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_session_entry CHECK (((type <> 5) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (subcontribution_id IS NULL) AND (session_id IS NOT NULL))));
    ''')
