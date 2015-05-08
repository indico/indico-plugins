"""Use FK for created_by_id

Revision ID: 16874c3e98a8
Revises: 35badbd96474
Create Date: 2015-05-08 14:45:51.811224
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '16874c3e98a8'
down_revision = '35badbd96474'


def upgrade():
    op.create_foreign_key(None,
                          'chatrooms', 'users',
                          ['created_by_id'], ['id'],
                          source_schema='plugin_chat', referent_schema='users')


def downgrade():
    op.drop_constraint('fk_chatrooms_created_by_id_users', 'chatrooms', schema='plugin_chat')
