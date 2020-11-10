# This file is part of the Indico plugins.
# Copyright (C) 2020 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_vc_zoom.controllers import RHRoomHost


blueprint = IndicoPluginBlueprint('vc_zoom', 'indico_vc_zoom')

# Room management
# using any(zoom) instead of defaults since the event vc room locator
# includes the service and normalization skips values provided in 'defaults'
blueprint.add_url_rule('/event/<confId>/manage/videoconference/zoom/<int:event_vc_room_id>/room-host',
                       'set_room_host', RHRoomHost, methods=('POST',))