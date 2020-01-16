# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from celery.schedules import crontab

from indico.core.celery import celery
from indico.core.db import db

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.util import clean_old_entries


@celery.periodic_task(run_every=crontab(minute='*/15'), plugin='livesync')
def scheduled_update():
    from indico_livesync.plugin import LiveSyncPlugin
    clean_old_entries()
    for agent in LiveSyncAgent.find_all():
        if agent.backend is None:
            LiveSyncPlugin.logger.warning('Skipping agent %s; backend not found', agent.name)
            continue
        if not agent.initial_data_exported:
            LiveSyncPlugin.logger.warning('Skipping agent %s; initial export not performed yet', agent.name)
            continue
        LiveSyncPlugin.logger.info('Running agent %s', agent.name)
        agent.create_backend().run()
        db.session.commit()
