"""Create extensions table

Revision ID: a702ad0bcea
Revises: None
Create Date: 2015-02-19 11:58:11.756966
"""

import sqlalchemy as sa
from alembic import op

from sqlalchemy.sql.ddl import CreateSchema, DropSchema


# revision identifiers, used by Alembic.
revision = 'a702ad0bcea'
down_revision = None


def upgrade():
    op.execute(CreateSchema('plugin_vc_vidyo'))
    op.create_table('vidyo_extensions',
                    sa.Column('vc_room_id', sa.Integer(), nullable=False),
                    sa.Column('extension', sa.BigInteger(), nullable=True, index=True),
                    sa.Column('owned_by_id', sa.Integer(), nullable=True, index=True),
                    sa.ForeignKeyConstraint(['vc_room_id'], ['events.vc_rooms.id']),
                    sa.PrimaryKeyConstraint('vc_room_id'),
                    schema='plugin_vc_vidyo')


def downgrade():
    op.drop_table('vidyo_extensions', schema='plugin_vc_vidyo')
    op.execute(DropSchema('plugin_vc_vidyo'))
