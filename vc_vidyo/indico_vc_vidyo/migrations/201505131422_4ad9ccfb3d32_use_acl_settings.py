"""Use ACL settings

Revision ID: 4ad9ccfb3d32
Revises: 3f376d68efc8
Create Date: 2015-05-13 14:22:09.748726
"""

from alembic import context

from indico.core.db.sqlalchemy.util.convert_acl_settings import json_to_acl, acl_to_json


# revision identifiers, used by Alembic.
revision = '4ad9ccfb3d32'
down_revision = '3f376d68efc8'


acl_settings = {'plugin_vc_vidyo.managers', 'plugin_vc_vidyo.acl'}


def upgrade():
    if context.is_offline_mode():
        raise Exception('This upgrade is only possible in online mode')
    json_to_acl(acl_settings)


def downgrade():
    if context.is_offline_mode():
        raise Exception('This downgrade is only possible in online mode')
    acl_to_json(acl_settings)
