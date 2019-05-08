# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_vc_vidyo.controllers import RHVidyoRoomOwner


blueprint = IndicoPluginBlueprint('vc_vidyo', 'indico_vc_vidyo')

# Room management
# using any(vidyo) instead of defaults since the event vc room locator
# includes the service and normalization skips values provided in 'defaults'
blueprint.add_url_rule('/event/<confId>/manage/videoconference/<any(vidyo):service>/<int:event_vc_room_id>/room-owner',
                       'set_room_owner', RHVidyoRoomOwner, methods=('POST',))
