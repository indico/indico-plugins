"""Add location_changed change type

Revision ID: 02a78555cdcb
Revises: d8e65cb6160d
Create Date: 2021-05-06 19:17:41.256096
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '02a78555cdcb'
down_revision = 'd8e65cb6160d'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        ALTER TABLE plugin_livesync.queues DROP CONSTRAINT "ck_queues_valid_enum_change";
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT "ck_queues_valid_enum_change" CHECK ((change = ANY (ARRAY[1, 2, 3, 4, 5, 6])));
    ''')


def downgrade():
    op.execute('DELETE FROM plugin_livesync.queues WHERE change = 6')
    op.execute('''
        ALTER TABLE plugin_livesync.queues DROP CONSTRAINT "ck_queues_valid_enum_change";
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT "ck_queues_valid_enum_change" CHECK ((change = ANY (ARRAY[1, 2, 3, 4, 5])));
    ''')
