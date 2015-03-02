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

from __future__ import unicode_literals

from indico.core.db.sqlalchemy import db
from indico.util.string import return_ascii
from MaKaC.user import AvatarHolder


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
    extension = db.Column(
        db.BigInteger,
        index=True
    )
    owned_by_id = db.Column(
        db.Integer,
        index=True,
    )
    vc_room = db.relationship(
        'VCRoom',
        backref=db.backref('vidyo_extension', cascade='all, delete-orphan', uselist=False, lazy=False),
        lazy=False
    )

    @property
    def owned_by_user(self):
        """The Avatar who owns the vidyo room."""
        return AvatarHolder().getById(str(self.owned_by_id))

    @owned_by_user.setter
    def owned_by_user(self, user):
        self.owned_by_id = int(user.getId())

    @return_ascii
    def __repr__(self):
        return '<VidyoExtension({}, {}, {})>'.format(self.vc_room, self.extension, self.owned_by_id)
