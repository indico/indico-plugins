"""Add table for predefined prompts for categories

Revision ID: e2bf94dfa64a
Revises:
Create Date: 2025-09-04 12:08:06.061611
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.ddl import CreateSchema, DropSchema


# revision identifiers, used by Alembic.
revision = 'e2bf94dfa64a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSchema('plugin_ai_summary'))
    op.create_table('predefined_prompts',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('category_id', sa.Integer(), nullable=False, index=True),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('text', sa.Text(), nullable=False),
                    sa.ForeignKeyConstraint(['category_id'], ['categories.categories.id']),
                    sa.PrimaryKeyConstraint('id'),
                    schema='plugin_ai_summary')


def downgrade():
    op.drop_table('predefined_prompts', schema='plugin_ai_summary')
    op.execute(DropSchema('plugin_ai_summary'))
