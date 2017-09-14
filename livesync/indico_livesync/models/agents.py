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

from sqlalchemy.dialects.postgresql import JSON

from indico.core.db.sqlalchemy import UTCDateTime, db
from indico.util.date_time import now_utc
from indico.util.string import return_ascii


class LiveSyncAgent(db.Model):
    __tablename__ = 'agents'
    __table_args__ = {'schema': 'plugin_livesync'}

    #: Agent ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    #: Agent backend (a key from `LiveSyncPlugin.agent_classes`)
    backend_name = db.Column(
        db.String,
        nullable=False
    )

    #: A pretty name for the agent
    name = db.Column(
        db.String,
        nullable=False
    )

    #: If the initial dataset has been exported yet
    initial_data_exported = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    #: Timestamp of the last run
    last_run = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )

    #: Backend-specific settings
    settings = db.Column(
        JSON,
        nullable=False,
        default={}
    )

    @property
    def locator(self):
        return {'agent_id': self.id}

    @property
    def backend(self):
        """Returns the backend class"""
        from indico_livesync.plugin import LiveSyncPlugin
        return LiveSyncPlugin.instance.backend_classes.get(self.backend_name)

    def create_backend(self):
        """Creates a new backend instance"""
        return self.backend(self)

    @return_ascii
    def __repr__(self):
        return '<LiveSyncAgent({}, {}, {})>'.format(self.id, self.backend_name, self.name)
