"""Add attachment_id to queue

Revision ID: d8e65cb6160d
Revises: 6ef9616e57cb
Create Date: 2021-04-27 13:59:11.538263
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd8e65cb6160d'
down_revision = '6ef9616e57cb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('queues', sa.Column('attachment_id', sa.Integer(), nullable=True, index=True), schema='plugin_livesync')
    op.create_foreign_key(None, 'queues', 'attachments', ['attachment_id'], ['id'], source_schema='plugin_livesync',
                          referent_schema='attachments')
    op.drop_constraint('ck_queues_valid_enum_type', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_session_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_note_entry', 'queues', schema='plugin_livesync')
    op.execute('''
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_enum_type CHECK ((type = ANY (ARRAY[1, 2, 3, 4, 5, 6, 7])));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_attachment_entry CHECK (((type <> 7) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (attachment_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_category_entry CHECK (((type <> 1) OR ((attachment_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (category_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_contribution_entry CHECK (((type <> 3) OR ((attachment_id IS NULL) AND (category_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (contribution_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_event_entry CHECK (((type <> 2) OR ((attachment_id IS NULL) AND (category_id IS NULL) AND (contribution_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (event_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_note_entry CHECK (((type <> 6) OR ((attachment_id IS NULL) AND (category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (note_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_session_entry CHECK (((type <> 5) OR ((attachment_id IS NULL) AND (category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (subcontribution_id IS NULL) AND (session_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_subcontribution_entry CHECK (((type <> 4) OR ((attachment_id IS NULL) AND (category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NOT NULL))));
    ''')


def downgrade():
    op.execute('DELETE FROM plugin_livesync.queues WHERE type = 7')

    op.drop_constraint('ck_queues_valid_enum_type', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_category_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_event_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_contribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_subcontribution_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_session_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_note_entry', 'queues', schema='plugin_livesync')
    op.drop_constraint('ck_queues_valid_attachment_entry', 'queues', schema='plugin_livesync')

    op.drop_column('queues', 'attachment_id', schema='plugin_livesync')

    op.execute('''
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_enum_type CHECK ((type = ANY (ARRAY[1, 2, 3, 4, 5, 6])));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_category_entry CHECK (((type <> 1) OR ((contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (category_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_contribution_entry CHECK (((type <> 3) OR ((category_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (contribution_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_event_entry CHECK (((type <> 2) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (event_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_note_entry CHECK (((type <> 6) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NULL) AND (note_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_session_entry CHECK (((type <> 5) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (subcontribution_id IS NULL) AND (session_id IS NOT NULL))));
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT ck_queues_valid_subcontribution_entry CHECK (((type <> 4) OR ((category_id IS NULL) AND (contribution_id IS NULL) AND (event_id IS NULL) AND (note_id IS NULL) AND (session_id IS NULL) AND (subcontribution_id IS NOT NULL))));
    ''')
