"""Add affiliations vector store.

Revision ID: f95cb312d2bb
Revises:
Create Date: 2026-03-13 12:43:32.863241
"""

import sqlalchemy as sa
from alembic import context, op
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql.ddl import CreateSchema, DropSchema


# revision identifiers, used by Alembic.
revision = 'f95cb312d2bb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if not context.is_offline_mode():
        connection = context.get_bind()
        # Make sure the vector extension is enabled
        result = connection.execute("SELECT oid FROM pg_extension where extname = 'vector'")
        if result.rowcount == 0:
            raise Exception('The pg_extension "vector" must be enabled to run this update')

    op.execute(CreateSchema('plugin_ror'))
    op.create_table('affiliation_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(dim=512), nullable=False),
        sa.Column('affiliation_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['affiliation_id'], ['indico.affiliations.id'], ondelete='cascade'),
        sa.PrimaryKeyConstraint('id'),
        schema='plugin_ror'
    )


def downgrade():
    op.drop_table('affiliation_documents', schema='plugin_ror')
    op.execute(DropSchema('plugin_ror'))
