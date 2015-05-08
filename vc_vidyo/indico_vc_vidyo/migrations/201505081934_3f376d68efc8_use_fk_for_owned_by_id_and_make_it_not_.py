"""Use FK for owned_by_id and make it NOT NULL

Revision ID: 3f376d68efc8
Revises: 3520616f8ff7
Create Date: 2015-05-08 19:34:25.491411
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '3f376d68efc8'
down_revision = '3520616f8ff7'


def upgrade():
    op.alter_column('vidyo_extensions', 'owned_by_id', nullable=False, schema='plugin_vc_vidyo')
    op.create_foreign_key(None,
                          'vidyo_extensions', 'users',
                          ['owned_by_id'], ['id'],
                          source_schema='plugin_vc_vidyo', referent_schema='users')


def downgrade():
    op.drop_constraint('fk_vidyo_extensions_owned_by_id_users', 'vidyo_extensions', schema='plugin_vc_vidyo')
    op.alter_column('vidyo_extensions', 'owned_by_id', nullable=True, schema='plugin_vc_vidyo')
