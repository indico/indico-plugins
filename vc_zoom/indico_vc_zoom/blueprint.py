# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_vc_zoom.controllers import RHRoomAlternativeHost, RHWebhook


blueprint = IndicoPluginBlueprint('vc_zoom', 'indico_vc_zoom')

# Room management
# using any(zoom) instead of defaults since the event vc room locator
# includes the service and normalization skips values provided in 'defaults'
blueprint.add_url_rule(
    '/event/<int:event_id>/manage/videoconference/<any(zoom):service>/<int:event_vc_room_id>/make-me-alt-host',
    'make_me_alt_host',
    RHRoomAlternativeHost,
    methods=('POST',)
)
blueprint.add_url_rule('/api/plugin/zoom/webhook', 'webhook', RHWebhook, methods=('POST',))
