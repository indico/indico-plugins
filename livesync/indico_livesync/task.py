# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from celery.schedules import crontab

from indico.core.celery import celery
from indico.core.db import db

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.util import clean_old_entries


@celery.periodic_task(run_every=crontab(minute='*/15'), plugin='livesync')
def scheduled_update():
    from indico_livesync.plugin import LiveSyncPlugin
    if LiveSyncPlugin.settings.get('disable_queue_runs'):
        LiveSyncPlugin.logger.warning('Queue runs are disabled')
        return
    clean_old_entries()
    for agent in LiveSyncAgent.query.all():
        if agent.backend is None:
            LiveSyncPlugin.logger.warning('Skipping agent %s; backend not found', agent.name)
            continue
        backend = agent.create_backend()
        queue_allowed, reason = backend.check_queue_status()
        if not queue_allowed:
            LiveSyncPlugin.logger.warning('Skipping agent %s; queue runs disabled: %s', agent.name, reason)
            continue
        LiveSyncPlugin.logger.info('Running agent %s', agent.name)
        backend.run()
        db.session.commit()
