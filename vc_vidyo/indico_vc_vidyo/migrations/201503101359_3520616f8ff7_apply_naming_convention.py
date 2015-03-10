"""Apply naming convention

Revision ID: 3520616f8ff7
Revises: a702ad0bcea
Create Date: 2015-03-10 13:59:53.955083
"""

from alembic import op

from indico.core.db.sqlalchemy.util.bulk_rename import bulk_rename


# revision identifiers, used by Alembic.
revision = '3520616f8ff7'
down_revision = 'a702ad0bcea'


mapping = {
    'plugin_vc_vidyo.vidyo_extensions': {
        'indexes': {
            'vidyo_extensions_pkey': 'pk_vidyo_extensions',
            'ix_plugin_vc_vidyo_vidyo_extensions_extension': 'ix_vidyo_extensions_extension',
            'ix_plugin_vc_vidyo_vidyo_extensions_owned_by_id': 'ix_vidyo_extensions_owned_by_id',
        },
        'constraints': {
            'vidyo_extensions_vc_room_id_fkey': 'fk_vidyo_extensions_vc_room_id_vc_rooms',
        }
    }
}


def upgrade():
    for stmt in bulk_rename(mapping):
        op.execute(stmt)


def downgrade():
    for stmt in bulk_rename(mapping, True):
        op.execute(stmt)
