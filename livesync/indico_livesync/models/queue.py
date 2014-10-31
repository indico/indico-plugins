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

from sqlalchemy.dialects.postgresql import JSON

from indico.core.db.sqlalchemy import db, UTCDateTime
from indico.util.date_time import now_utc
from indico.util.string import return_ascii

from indico_livesync.models.agents import LiveSyncAgent


class LiveSyncQueueEntry(db.Model):
    __tablename__ = 'queues'
    __table_args__ = {'schema': 'plugin_livesync'}

    #: Entry ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    #: ID of the agent this entry belongs to
    agent_id = db.Column(
        db.Integer,
        db.ForeignKey('plugin_livesync.agents.id'),
        index=True
    )

    #: Timestamp of the change
    timestamp = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )

    # XXX: maybe use an Enum for this?
    # XXX: or should it be an array? old code seems to have records with multiple changes
    #: the change type
    change = db.Column(
        db.String,
        nullable=False
    )

    #: Data related to the change
    data = db.Column(
        JSON,
        nullable=False,
    )

    #: The associated :class:LiveSyncAgent
    agent = db.relationship(
        'LiveSyncAgent',
        backref=db.backref('queue', cascade='all, delete-orphan', lazy='dynamic')
    )

    @return_ascii
    def __repr__(self):
        return '<LiveSyncQueueEntry({}, {}, {}, {})>'.format(self.agent, self.id, self.change, self.data)

    @classmethod
    def create(cls, change, data):
        """Creates a new change in all queues

        :param change: the change type
        :param data: the associated data (a json-serializable object)
        """
        for agent in LiveSyncAgent.find():
            db.session.add(cls(agent=agent, change=change, data=data))
        db.session.flush()
