"""Create tables

Revision ID: 1bd6c5129d29
Revises: None
Create Date: 2014-09-29 15:24:03.369025
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.ddl import CreateSchema, DropSchema

from indico.core.db.sqlalchemy import UTCDateTime


# revision identifiers, used by Alembic.
revision = '1bd6c5129d29'
down_revision = None


def upgrade():
    op.execute(CreateSchema('plugin_chat'))
    op.create_table('chatrooms',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('jid_node', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('description', sa.Text(), nullable=False),
                    sa.Column('password', sa.String(), nullable=False),
                    sa.Column('custom_server', sa.String(), nullable=False),
                    sa.Column('created_by_id', sa.Integer(), nullable=False),
                    sa.Column('created_dt', UTCDateTime(), nullable=False),
                    sa.Column('modified_dt', UTCDateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id', name='chatrooms_pkey'),
                    sa.UniqueConstraint('jid_node', 'custom_server', name='chatrooms_jid_node_custom_server_key'),
                    sa.Index('ix_plugin_chat_chatrooms_created_by_id', 'created_by_id'),
                    schema='plugin_chat')
    op.create_table('chatroom_events',
                    sa.Column('event_id', sa.Integer(), nullable=False, autoincrement=False),
                    sa.Column('chatroom_id', sa.Integer(), nullable=False),
                    sa.Column('hidden', sa.Boolean(), nullable=False),
                    sa.Column('show_password', sa.Boolean(), nullable=False),
                    sa.ForeignKeyConstraint(['chatroom_id'], ['plugin_chat.chatrooms.id'],
                                            name='chatroom_events_chatroom_id_fkey'),
                    sa.PrimaryKeyConstraint('event_id', 'chatroom_id', name='chatroom_events_pkey'),
                    sa.Index('ix_plugin_chat_chatroom_events_event_id', 'event_id'),
                    sa.Index('ix_plugin_chat_chatroom_events_chatroom_id', 'chatroom_id'),
                    schema='plugin_chat')


def downgrade():
    op.drop_table('chatroom_events', schema='plugin_chat')
    op.drop_table('chatrooms', schema='plugin_chat')
    op.execute(DropSchema('plugin_chat'))
