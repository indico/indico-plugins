# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from sqlalchemy.dialects.postgresql import JSON

from indico.core.db.sqlalchemy import UTCDateTime, db
from indico.util.date_time import now_utc


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

    def __repr__(self):
        return f'<LiveSyncAgent({self.id}, {self.backend_name}, {self.name})>'
