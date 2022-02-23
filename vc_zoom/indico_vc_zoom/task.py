# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import datetime

from indico.core import signals
from indico.core.celery import celery
from vc_zoom.indico_vc_zoom.api import ZoomIndicoClient
from vc_zoom.indico_vc_zoom.util import ZoomMeetingType


@signals.event.updated.connect
@signals.event.contribution_updated.connect
@signals.event.session_block_updated.connect
def check_meetings(target, changes):
    if 'start_dt' not in changes:
        return
    prev_date, new_date = changes.get('start_dt')
    if new_date < prev_date:
        return
    refresh_meetings.delay(target.vc_room_associations, target.start_dt)


@celery.task(name='reschedule_meeting', plugin='vc_zoom')
def refresh_meetings(vc_rooms, target_dt):
    client = ZoomIndicoClient()
    vc_rooms = [room for room in vc_rooms if room.vc_room.type == 'zoom'
                and room.data['meeting_type'] == ZoomMeetingType.scheduled_meeting]
    if not vc_rooms:
        return
    meeting = client.get_meeting(vc_rooms[0].data['zoom_id'])
    start_dt = datetime.datetime.fromisoformat(meeting['start_time'].replace("Z", "+00:00"))
    if target_dt < start_dt.replace(tzinfo=None) + datetime.timedelta(days=30):
        return
    for vc_room in vc_rooms:
        serialized_date = target_dt.replace(microsecond=0).isoformat() + 'Z'
        client.update_meeting(vc_room.data['zoom_id'], {'start_time': serialized_date})
