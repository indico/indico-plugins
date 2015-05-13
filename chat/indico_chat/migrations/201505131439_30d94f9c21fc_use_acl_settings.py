"""Use ACL settings

Revision ID: 30d94f9c21fc
Revises: 16874c3e98a8
Create Date: 2015-05-13 14:39:18.659784
"""

from alembic import context

from indico.core.db.sqlalchemy.util.convert_acl_settings import json_to_acl, acl_to_json


# revision identifiers, used by Alembic.
revision = '30d94f9c21fc'
down_revision = '16874c3e98a8'


acl_settings = {'plugin_chat.admins'}


def upgrade():
    if context.is_offline_mode():
        raise Exception('This upgrade is only possible in online mode')
    json_to_acl(acl_settings)


def downgrade():
    if context.is_offline_mode():
        raise Exception('This downgrade is only possible in online mode')
    acl_to_json(acl_settings)
