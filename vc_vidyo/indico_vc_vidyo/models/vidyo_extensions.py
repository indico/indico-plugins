# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from indico.core.db.sqlalchemy import db


class VidyoExtension(db.Model):
    __tablename__ = 'vidyo_extensions'
    __table_args__ = {'schema': 'plugin_vc_vidyo'}

    #: ID of the video conference room
    vc_room_id = db.Column(
        db.Integer,
        db.ForeignKey('events.vc_rooms.id'),
        primary_key=True,
        index=True
    )
    value = db.Column(
        db.String,
        index=True
    )
    vc_room = db.relationship(
        'VCRoom',
        backref=db.backref('vidyo_extension', cascade='all, delete-orphan', uselist=False, lazy=False),
        lazy=False
    )
