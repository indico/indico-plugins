"""Create tables

Revision ID: 3888761f35f7
Revises:
Create Date: 2017-06-30 15:51:54.477207
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.ddl import CreateSchema, DropSchema

from indico.core.db.sqlalchemy import UTCDateTime


# revision identifiers, used by Alembic.
revision = '3888761f35f7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSchema('plugin_chat'))
    op.create_table('chatrooms',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('jid_node', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('description', sa.Text(), nullable=False),
                    sa.Column('password', sa.String(), nullable=False),
                    sa.Column('custom_server', sa.String(), nullable=False),
                    sa.Column('created_by_id', sa.Integer(), nullable=False, index=True),
                    sa.Column('created_dt', UTCDateTime, nullable=False),
                    sa.Column('modified_dt', UTCDateTime, nullable=True),
                    sa.ForeignKeyConstraint(['created_by_id'], ['users.users.id']),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('jid_node', 'custom_server'),
                    schema='plugin_chat')
    op.create_table('chatroom_events',
                    sa.Column('event_id', sa.Integer(), autoincrement=False, nullable=False, index=True),
                    sa.Column('chatroom_id', sa.Integer(), autoincrement=False, nullable=False, index=True),
                    sa.Column('hidden', sa.Boolean(), nullable=False),
                    sa.Column('show_password', sa.Boolean(), nullable=False),
                    sa.ForeignKeyConstraint(['chatroom_id'], ['plugin_chat.chatrooms.id']),
                    sa.ForeignKeyConstraint(['event_id'], ['events.events.id']),
                    sa.PrimaryKeyConstraint('event_id', 'chatroom_id'),
                    schema='plugin_chat')


def downgrade():
    op.drop_table('chatroom_events', schema='plugin_chat')
    op.drop_table('chatrooms', schema='plugin_chat')
    op.execute(DropSchema('plugin_chat'))
