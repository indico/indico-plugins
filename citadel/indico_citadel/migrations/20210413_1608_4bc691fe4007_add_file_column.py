"""Add file column

Revision ID: 4bc691fe4007
Revises: 0cf18be7ade1
Create Date: 2021-04-13 16:08:59.013204
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '4bc691fe4007'
down_revision = '0cf18be7ade1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('es_id_map', sa.Column('attachment_file_id', sa.Integer(), nullable=True), schema='plugin_citadel')
    op.create_index(op.f('ix_es_id_map_attachment_file_id'), 'es_id_map', ['attachment_file_id'],
                    unique=False, schema='plugin_citadel')
    op.create_foreign_key(op.f('fk_es_id_map_attachment_file_id_files'), 'es_id_map', 'files', ['attachment_file_id'],
                          ['id'], source_schema='plugin_citadel', referent_schema='attachments')


def downgrade():
    op.drop_constraint(op.f('fk_es_id_map_attachment_file_id_files'), 'es_id_map',
                       schema='plugin_citadel', type_='foreignkey')
    op.drop_index(op.f('ix_es_id_map_attachment_file_id'), table_name='es_id_map', schema='plugin_citadel')
    op.drop_column('es_id_map', 'attachment_file_id', schema='plugin_citadel')
