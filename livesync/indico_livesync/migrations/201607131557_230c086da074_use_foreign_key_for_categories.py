"""Use foreign key for categories

Revision ID: 230c086da074
Revises: 2c9618a7a2ea
Create Date: 2016-07-13 15:57:49.911262
"""

from alembic import op


revision = '230c086da074'
down_revision = '2c9618a7a2ea'


def upgrade():
    op.create_foreign_key(None,
                          'queues', 'categories',
                          ['category_id'], ['id'],
                          source_schema='plugin_livesync', referent_schema='categories')


def downgrade():
    op.drop_constraint('fk_queues_category_id_categories', 'queues', schema='plugin_livesync')
