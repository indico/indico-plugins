"""Apply naming convention

Revision ID: 5a9176bca07d
Revises: 1c2b0e17447d
Create Date: 2015-03-10 13:51:26.353667
"""

from alembic import op

from indico.core.db.sqlalchemy.util.bulk_rename import bulk_rename


# revision identifiers, used by Alembic.
revision = '5a9176bca07d'
down_revision = '1c2b0e17447d'


mapping = {
    'plugin_livesync.agents': {
        'indexes': {
            'agents_pkey': 'pk_agents',
        }
    },
    'plugin_livesync.queues': {
        'indexes': {
            'queues_pkey': 'pk_queues',
            'ix_plugin_livesync_queues_agent_id': 'ix_queues_agent_id',
        },
        'constraints': {
            'queues_change_check': 'ck_queues_valid_enum_change',
            'queues_agent_id_fkey': 'fk_queues_agent_id_agents',
        }
    },
}


def upgrade():
    for stmt in bulk_rename(mapping):
        op.execute(stmt)


def downgrade():
    for stmt in bulk_rename(mapping, True):
        op.execute(stmt)
