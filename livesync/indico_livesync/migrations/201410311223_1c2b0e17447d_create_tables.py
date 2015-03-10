"""Create tables

Revision ID: 1c2b0e17447d
Revises: None
Create Date: 2014-10-31 12:23:21.956730
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.ddl import CreateSchema, DropSchema

from indico.core.db.sqlalchemy import UTCDateTime, PyIntEnum
from indico.core.db.sqlalchemy.util.bulk_rename import _rename_constraint

from indico_livesync.models.queue import ChangeType


# revision identifiers, used by Alembic.
revision = '1c2b0e17447d'
down_revision = None


def upgrade():
    op.execute(CreateSchema('plugin_livesync'))
    op.create_table('agents',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('backend_name', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('initial_data_exported', sa.Boolean(), nullable=False),
                    sa.Column('last_run', UTCDateTime(), nullable=False),
                    sa.Column('settings', postgresql.JSON(), nullable=False),
                    sa.PrimaryKeyConstraint('id', name='agents_pkey'),
                    schema='plugin_livesync')
    op.create_table('queues',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('agent_id', sa.Integer(), nullable=False),
                    sa.Column('timestamp', UTCDateTime(), nullable=False),
                    sa.Column('processed', sa.Boolean(), nullable=False),
                    sa.Column('change', PyIntEnum(ChangeType), nullable=False),
                    sa.Column('type', sa.String(), nullable=False),
                    sa.Column('category_id', sa.String()),
                    sa.Column('event_id', sa.String()),
                    sa.Column('contrib_id', sa.String()),
                    sa.Column('subcontrib_id', sa.String()),
                    sa.ForeignKeyConstraint(['agent_id'], ['plugin_livesync.agents.id'], name='queues_agent_id_fkey'),
                    sa.PrimaryKeyConstraint('id', name='queues_pkey'),
                    sa.Index('ix_plugin_livesync_queues_agent_id', 'agent_id'),
                    schema='plugin_livesync')
    # later migrations expect the old name...
    op.execute(_rename_constraint('plugin_livesync', 'queues', 'ck_queues_valid_enum_change', 'queues_change_check'))


def downgrade():
    op.drop_table('queues', schema='plugin_livesync')
    op.drop_table('agents', schema='plugin_livesync')
    op.execute(DropSchema('plugin_livesync'))
