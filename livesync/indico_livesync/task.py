# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from indico.core.db import DBMgr
from indico.modules.scheduler.tasks.periodic import PeriodicUniqueTask
from indico.util.date_time import now_utc

from indico_livesync.models.agents import LiveSyncAgent


class LiveSyncTask(PeriodicUniqueTask):
    DISABLE_ZODB_HOOK = True

    @property
    def logger(self):
        return self.getLogger()

    def extend_runtime(self):
        # Make the task manager believe the task is running since a much shorter time
        self.setOnRunningListSince(now_utc())
        DBMgr.getInstance().commit()

    def run(self):
        from indico_livesync.plugin import LiveSyncPlugin

        plugin = LiveSyncPlugin.instance  # RuntimeError if not active
        with plugin.plugin_context():
            for agent in LiveSyncAgent.find_all():
                if not agent.initial_data_exported:
                    self.logger.warning('Skipping agent {}; initial export not performed yet'.format(agent.name))
                    continue
                with DBMgr.getInstance().global_connection():
                    self.logger.info('Running agent {}'.format(agent.name))
                    agent.create_backend(self).run()
