# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_owncloud.controllers import RHAddCategoryAttachmentOwncloud, RHAddEventAttachmentOwncloud


blueprint = IndicoPluginBlueprint('owncloud', 'indico_owncloud')
blueprint.add_url_rule('/category/<int:category_id>/manage/attachments/add/owncloud', 'owncloud_category',
                       RHAddCategoryAttachmentOwncloud, methods=('GET', 'POST'), defaults={'object_type': 'category'})
blueprint.add_url_rule('/event/<int:event_id>/manage/attachments/add/owncloud', 'owncloud_event',
                       RHAddEventAttachmentOwncloud, methods=('GET', 'POST'), defaults={'object_type': 'event'})
