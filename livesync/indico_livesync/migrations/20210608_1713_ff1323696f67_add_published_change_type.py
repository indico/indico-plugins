"""Add published/unpublished change types

Revision ID: ff1323696f67
Revises: 330e32d26232
Create Date: 2021-06-08 17:13:48.935771
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'ff1323696f67'
down_revision = '330e32d26232'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        ALTER TABLE plugin_livesync.queues DROP CONSTRAINT "ck_queues_valid_enum_change";
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT "ck_queues_valid_enum_change" CHECK ((change = ANY (ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9])));
    ''')


def downgrade():
    op.execute('DELETE FROM plugin_livesync.queues WHERE change IN (8, 9)')
    op.execute('''
        ALTER TABLE plugin_livesync.queues DROP CONSTRAINT "ck_queues_valid_enum_change";
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT "ck_queues_valid_enum_change" CHECK ((change = ANY (ARRAY[1, 2, 3, 4, 5, 6, 7])));
    ''')
