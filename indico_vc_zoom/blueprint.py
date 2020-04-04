

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_vc_zoom.controllers import RHZoomRoomOwner


blueprint = IndicoPluginBlueprint('vc_zoom', 'indico_vc_zoom')

# Room management
# using any(zoom) instead of defaults since the event vc room locator
# includes the service and normalization skips values provided in 'defaults'
blueprint.add_url_rule('/event/<confId>/manage/videoconference/<any(zoom):service>/<int:event_vc_room_id>/room-owner',
                       'set_room_owner', RHZoomRoomOwner, methods=('POST',))
