"""Create tables

Revision ID: 6019621fea50
Revises:
Create Date: 2017-06-30 16:11:31.486845
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.ddl import CreateSchema, DropSchema


# revision identifiers, used by Alembic.
revision = '6019621fea50'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSchema('plugin_vc_vidyo'))
    op.create_table('vidyo_extensions',
                    sa.Column('vc_room_id', sa.Integer(), nullable=False),
                    sa.Column('extension', sa.BigInteger(), nullable=True, index=True),
                    sa.Column('owned_by_id', sa.Integer(), nullable=False, index=True),
                    sa.ForeignKeyConstraint(['owned_by_id'], ['users.users.id']),
                    sa.ForeignKeyConstraint(['vc_room_id'], ['events.vc_rooms.id']),
                    sa.PrimaryKeyConstraint('vc_room_id'),
                    schema='plugin_vc_vidyo')


def downgrade():
    op.drop_table('vidyo_extensions', schema='plugin_vc_vidyo')
    op.execute(DropSchema('plugin_vc_vidyo'))
