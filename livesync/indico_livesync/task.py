# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

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
