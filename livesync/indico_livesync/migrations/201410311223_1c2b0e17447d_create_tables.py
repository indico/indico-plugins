"""Create tables

Revision ID: 1c2b0e17447d
Revises: None
Create Date: 2014-10-31 12:23:21.956730
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.ddl import CreateSchema, DropSchema

from indico.core.db.sqlalchemy import UTCDateTime


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
                    sa.Column('settings', postgresql.JSON(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    schema='plugin_livesync')
    op.create_table('queues',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('agent_id', sa.Integer(), nullable=False, index=True),
                    sa.Column('timestamp', UTCDateTime(), nullable=False),
                    sa.Column('change', sa.SmallInteger(), nullable=False),
                    sa.Column('type', sa.String(), nullable=False),
                    sa.Column('category_id', sa.String()),
                    sa.Column('event_id', sa.String()),
                    sa.Column('contrib_id', sa.String()),
                    sa.Column('subcontrib_id', sa.String()),
                    sa.ForeignKeyConstraint(['agent_id'], ['plugin_livesync.agents.id']),
                    sa.CheckConstraint('change IN (1, 2, 3, 4, 5, 6)'),
                    sa.PrimaryKeyConstraint('id'),
                    schema='plugin_livesync')


def downgrade():
    op.drop_table('queues', schema='plugin_livesync')
    op.drop_table('agents', schema='plugin_livesync')
    op.execute(DropSchema('plugin_livesync'))
