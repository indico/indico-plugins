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

from indico.core.db.sqlalchemy import db, UTCDateTime
from indico.util.date_time import now_utc
from indico.util.string import return_ascii
from indico.util.struct.enum import IndicoEnum

from indico_livesync.models.agents import LiveSyncAgent


class ChangeType(int, IndicoEnum):
    created = 1
    deleted = 2
    moved = 3
    data_changed = 4
    title_changed = 5
    protection_changed = 6


class LiveSyncQueueEntry(db.Model):
    __tablename__ = 'queues'
    __table_args__ = (db.CheckConstraint('change IN ({})'.format(', '.join(map(str, ChangeType)))),
                      {'schema': 'plugin_livesync'})

    #: Entry ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    #: ID of the agent this entry belongs to
    agent_id = db.Column(
        db.Integer,
        db.ForeignKey('plugin_livesync.agents.id'),
        nullable=False,
        index=True
    )

    #: Timestamp of the change
    timestamp = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )

    #: the change type, a :class:`ChangeType`
    change = db.Column(
        db.SmallInteger,
        nullable=False
    )

    #: The ID of the changed category
    category_id = db.Column(
        db.String,
        nullable=True
    )

    #: The event ID of the changed event/contribution/subcontribution
    event_id = db.Column(
        db.String,
        nullable=True
    )

    #: The contribution ID of the changed contribution/subcontribution
    contrib_id = db.Column(
        db.String,
        nullable=True
    )

    #: The subcontribution ID of the changed subcontribution
    subcontrib_id = db.Column(
        db.String,
        nullable=True
    )

    #: The associated :class:LiveSyncAgent
    agent = db.relationship(
        'LiveSyncAgent',
        backref=db.backref('queue', cascade='all, delete-orphan', lazy='dynamic')
    )

    @return_ascii
    def __repr__(self):
        return '<LiveSyncQueueEntry({}, {}, {}, {})>'.format(self.agent, self.id, ChangeType(self.change).name,
                                                             self.data)

    @classmethod
    def create(cls, changes, obj_ref):
        """Creates a new change in all queues

        :param changes: the change types, an iterable containing
                        :class:`ChangeType`
        :param obj_ref: the object reference (returned by `obj_ref`)
                        of the changed object
        """
        obj_ref = dict(obj_ref)
        obj_ref.pop('type')
        for agent in LiveSyncAgent.find():
            for change in changes:
                entry = cls(agent=agent, change=change, **obj_ref)
                db.session.add(entry)
        db.session.flush()
