"""Use proper FK for event_id

Revision ID: 685f2016cd0
Revises: 30d94f9c21fc
Create Date: 2015-09-24 12:01:59.704121
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '685f2016cd0'
down_revision = '30d94f9c21fc'


def upgrade():
    # delete orphaned payment chatroom associations
    op.execute("DELETE FROM plugin_chat.chatroom_events ce WHERE NOT EXISTS "
               "(SELECT 1 FROM events.events e WHERE e.id = ce.event_id)")
    op.create_foreign_key(None,
                          'chatroom_events', 'events',
                          ['event_id'], ['id'],
                          source_schema='plugin_chat', referent_schema='events')


def downgrade():
    op.drop_constraint('fk_chatroom_events_event_id_events', 'chatroom_events', schema='plugin_chat')
