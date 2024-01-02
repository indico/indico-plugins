# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools

from indico.core.plugins import IndicoPluginBlueprint
from indico.modules.attachments.blueprint import _dispatch
from indico.modules.events import event_management_object_url_prefixes

from indico_owncloud.controllers import RHAddCategoryAttachmentOwncloud, RHAddEventAttachmentOwncloud


blueprint = IndicoPluginBlueprint('owncloud', 'indico_owncloud')


items = itertools.chain(event_management_object_url_prefixes.items(), [('category', ['/manage'])])
for object_type, prefixes in items:
    for prefix in prefixes:
        if object_type == 'category':
            prefix = '/category/<int:category_id>' + prefix
        else:
            prefix = '/event/<int:event_id>' + prefix
        blueprint.add_url_rule(prefix + '/attachments/add/owncloud', 'upload_owncloud',
                               _dispatch(RHAddEventAttachmentOwncloud, RHAddCategoryAttachmentOwncloud),
                               methods=('GET', 'POST'), defaults={'object_type': object_type})
