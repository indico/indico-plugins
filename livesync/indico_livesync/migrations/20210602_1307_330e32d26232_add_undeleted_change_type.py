"""Add undeleted change type

Revision ID: 330e32d26232
Revises: 02a78555cdcb
Create Date: 2021-06-02 13:07:48.837833
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '330e32d26232'
down_revision = '02a78555cdcb'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        ALTER TABLE plugin_livesync.queues DROP CONSTRAINT "ck_queues_valid_enum_change";
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT "ck_queues_valid_enum_change" CHECK ((change = ANY (ARRAY[1, 2, 3, 4, 5, 6, 7])));
    ''')


def downgrade():
    op.execute('DELETE FROM plugin_livesync.queues WHERE change = 7')
    op.execute('''
        ALTER TABLE plugin_livesync.queues DROP CONSTRAINT "ck_queues_valid_enum_change";
        ALTER TABLE plugin_livesync.queues ADD CONSTRAINT "ck_queues_valid_enum_change" CHECK ((change = ANY (ARRAY[1, 2, 3, 4, 5, 6])));
    ''')
