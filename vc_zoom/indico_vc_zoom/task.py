# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2024 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import time

from celery.schedules import crontab
from requests.exceptions import HTTPError
from sqlalchemy.orm.attributes import flag_modified

from indico.core.celery import celery
from indico.core.db import db

from indico_vc_zoom.api.client import get_zoom_token


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


@celery.periodic_task(run_every=crontab(minute='*/5'), plugin='vc_zoom')
def refresh_token(threshold=600):
    from indico_vc_zoom.plugin import ZoomPlugin

    config = ZoomPlugin.settings.get_all()
    if not all(config[x] for x in ('account_id', 'client_id', 'client_secret')):
        # not using oauth -> nothing to do
        return

    expires_at = get_zoom_token(config)[1]
    expires_in = int(expires_at - time.time())
    if expires_in > threshold:
        ZoomPlugin.logger.debug('Token expires in %ds, not renewing yet', expires_in)
        return

    ZoomPlugin.logger.info('Token expires in %ds, getting a new one', expires_in)
    get_zoom_token(config, force=True)
