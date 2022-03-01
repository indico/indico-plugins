# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core import signals
from indico.core.db import db
from indico.modules.logs import EventLogRealm, LogKind
from indico.util.i18n import make_bound_gettext

from indico_vc_zoom.task import refresh_meetings


_ = make_bound_gettext('vc_zoom')


@signals.event.updated.connect
@signals.event.contribution_updated.connect
@signals.event.session_block_updated.connect
def check_meetings(target, changes):
    if 'start_dt' not in changes:
        return
    zoom_rooms = [room.vc_room for room in target.vc_room_associations if room.vc_room.type == 'zoom']
    log_entry = target.log(EventLogRealm.event, LogKind.change, 'Videoconference', 'Schedule updated', data={
        'Meetings': ','.join([f'{room.name} (ID: {room.id})' for room in zoom_rooms]),
        'Date': target.start_dt.isoformat(),
        'State': 'pending'
    })
    db.session.commit()
    refresh_meetings.delay(zoom_rooms, target.start_dt, log_entry)
