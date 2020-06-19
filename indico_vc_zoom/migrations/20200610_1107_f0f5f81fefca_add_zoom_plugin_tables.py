"""Add Zoom plugin tables.

Revision ID: f0f5f81fefca
Revises:
Create Date: 2020-06-10 11:07:58.821382
"""

import sqlalchemy as sa
from alembic import op

from sqlalchemy.sql.ddl import CreateSchema, DropSchema


# revision identifiers, used by Alembic.
revision = 'f0f5f81fefca'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSchema('plugin_vc_zoom'))
    op.create_table(
        'zoom_meetings',
        sa.Column('vc_room_id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting', sa.BigInteger(), nullable=True, index=True),
        sa.Column('url_zoom', sa.String(), nullable=False),
        sa.Column('owned_by_id', sa.Integer(), nullable=False, index=True),
        sa.ForeignKeyConstraint(['owned_by_id'], [u'users.users.id'],
                                name=op.f('fk_zoom_meetings_owned_by_id_users')),
        sa.ForeignKeyConstraint(['vc_room_id'], [u'events.vc_rooms.id'],
                                name=op.f('fk_zoom_meetings_vc_room_id_vc_rooms')),
        schema='plugin_vc_zoom'
    )


def downgrade():
    op.drop_table('zoom_meetings', schema='plugin_vc_zoom')
    op.execute(DropSchema('plugin_vc_zoom'))
