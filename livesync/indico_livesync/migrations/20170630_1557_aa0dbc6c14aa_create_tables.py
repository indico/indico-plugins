"""Create tables

Revision ID: aa0dbc6c14aa
Revises:
Create Date: 2017-06-30 15:57:09.132083
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.ddl import CreateSchema, DropSchema

from indico.core.db.sqlalchemy import PyIntEnum, UTCDateTime

from indico_livesync.models.queue import ChangeType, EntryType


# revision identifiers, used by Alembic.
revision = 'aa0dbc6c14aa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSchema('plugin_livesync'))
    op.create_table('agents',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('backend_name', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('initial_data_exported', sa.Boolean(), nullable=False),
                    sa.Column('last_run', UTCDateTime, nullable=False),
                    sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    schema='plugin_livesync')
    op.create_table('queues',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('agent_id', sa.Integer(), nullable=False, index=True),
                    sa.Column('timestamp', UTCDateTime, nullable=False),
                    sa.Column('processed', sa.Boolean(), nullable=False),
                    sa.Column('change', PyIntEnum(ChangeType), nullable=False),
                    sa.Column('type', PyIntEnum(EntryType), nullable=False),
                    sa.Column('category_id', sa.Integer(), nullable=True, index=True),
                    sa.Column('event_id', sa.Integer(), nullable=True, index=True),
                    sa.Column('contribution_id', sa.Integer(), nullable=True, index=True),
                    sa.Column('session_id', sa.Integer(), nullable=True, index=True),
                    sa.Column('subcontribution_id', sa.Integer(), nullable=True, index=True),
                    sa.CheckConstraint('type != 1 OR (contribution_id IS NULL AND event_id IS NULL AND session_id '
                                       'IS NULL AND subcontribution_id IS NULL AND category_id IS NOT NULL)',
                                       name='valid_category_entry'),
                    sa.CheckConstraint('type != 2 OR (category_id IS NULL AND contribution_id IS NULL AND session_id '
                                       'IS NULL AND subcontribution_id IS NULL AND event_id IS NOT NULL)',
                                       name='valid_event_entry'),
                    sa.CheckConstraint('type != 3 OR (category_id IS NULL AND event_id IS NULL AND session_id '
                                       'IS NULL AND subcontribution_id IS NULL AND contribution_id IS NOT NULL)',
                                       name='valid_contribution_entry'),
                    sa.CheckConstraint('type != 4 OR (category_id IS NULL AND contribution_id IS NULL AND event_id '
                                       'IS NULL AND session_id IS NULL AND subcontribution_id IS NOT NULL)',
                                       name='valid_subcontribution_entry'),
                    sa.CheckConstraint('type != 5 OR (category_id IS NULL AND contribution_id IS NULL AND event_id '
                                       'IS NULL AND subcontribution_id IS NULL AND session_id IS NOT NULL)',
                                       name='valid_session_entry'),
                    sa.ForeignKeyConstraint(['agent_id'], ['plugin_livesync.agents.id']),
                    sa.ForeignKeyConstraint(['category_id'], ['categories.categories.id']),
                    sa.ForeignKeyConstraint(['contribution_id'], ['events.contributions.id']),
                    sa.ForeignKeyConstraint(['event_id'], ['events.events.id']),
                    sa.ForeignKeyConstraint(['session_id'], ['events.sessions.id']),
                    sa.ForeignKeyConstraint(['subcontribution_id'], ['events.subcontributions.id']),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk_queues')),
                    schema='plugin_livesync')


def downgrade():
    op.drop_table('queues', schema='plugin_livesync')
    op.drop_table('agents', schema='plugin_livesync')
    op.execute(DropSchema('plugin_livesync'))
