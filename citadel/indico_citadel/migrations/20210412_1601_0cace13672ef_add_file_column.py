"""add file column

Revision ID: 0cace13672ef
Revises: 0cf18be7ade1
Create Date: 2021-04-12 16:01:10.487607
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '0cace13672ef'
down_revision = '0cf18be7ade1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('es_id_map', sa.Column('file', sa.Integer(), nullable=True), schema='plugin_citadel')


def downgrade():
    op.drop_column('es_id_map', 'file', schema='plugin_citadel')
