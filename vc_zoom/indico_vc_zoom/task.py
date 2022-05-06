# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from requests.exceptions import HTTPError
from sqlalchemy.orm.attributes import flag_modified

from indico.core.celery import celery
from indico.core.db import db


def update_state_log(log_entry, failed):
    log_entry.data['State'] = 'failed' if failed else 'succeeded'
    flag_modified(log_entry, 'data')


@celery.task(plugin='vc_zoom', autoretry_for=(HTTPError,))
def refresh_meetings(vc_rooms, obj, log_entry=None):
    from indico_vc_zoom.api import ZoomIndicoClient
    client = ZoomIndicoClient()
    failed = False
    payload = {'start_time': obj.start_dt}
    if duration := int(obj.duration.total_seconds() / 60):
        payload['duration'] = duration
    try:
        for vc_room in vc_rooms:
            client.update_meeting(vc_room.data['zoom_id'], payload)
    except Exception:
        failed = True
        raise
    finally:
        if log_entry:
            update_state_log(log_entry, failed)
            db.session.commit()
