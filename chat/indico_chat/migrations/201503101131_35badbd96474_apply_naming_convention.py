"""Apply naming convention

Revision ID: 35badbd96474
Revises: 1bd6c5129d29
Create Date: 2015-03-10 11:31:42.850496
"""

from alembic import op

from indico.core.db.sqlalchemy.util.bulk_rename import bulk_rename


# revision identifiers, used by Alembic.
revision = '35badbd96474'
down_revision = '1bd6c5129d29'


mapping = {
    'plugin_chat.chatroom_events': {
        'indexes': {
            'chatroom_events_pkey': 'pk_chatroom_events',
            'ix_plugin_chat_chatroom_events_chatroom_id': 'ix_chatroom_events_chatroom_id',
            'ix_plugin_chat_chatroom_events_event_id': 'ix_chatroom_events_event_id',
        },
        'constraints': {
            'chatroom_events_chatroom_id_fkey': 'fk_chatroom_events_chatroom_id_chatrooms',
        }
    },
    'plugin_chat.chatrooms': {
        'indexes': {
            'chatrooms_pkey': 'pk_chatrooms',
            'ix_plugin_chat_chatrooms_created_by_id': 'ix_chatrooms_created_by_id',
        },
        'constraints': {
            'chatrooms_jid_node_custom_server_key': 'uq_chatrooms_jid_node_custom_server',
        }
    }
}


def upgrade():
    for stmt in bulk_rename(mapping):
        op.execute(stmt)


def downgrade():
    for stmt in bulk_rename(mapping, True):
        op.execute(stmt)
