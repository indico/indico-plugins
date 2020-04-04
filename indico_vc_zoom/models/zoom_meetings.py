

from __future__ import unicode_literals

import urllib

from sqlalchemy.event import listens_for
from sqlalchemy.orm.attributes import flag_modified

from indico.core.db.sqlalchemy import db
from indico.util.string import return_ascii


class ZoomMeeting(db.Model):
    __tablename__ = 'zoom_meetings'
    __table_args__ = {'schema': 'plugin_vc_zoom'}

    #: ID of the videoconference room
    vc_room_id = db.Column(
        db.Integer,
        db.ForeignKey('events.vc_rooms.id'),
        primary_key=True
    )
    meeting = db.Column(
        db.BigInteger,
        index=True
    )
    url_zoom = db.Column(
        db.Text,
        index=True,
        nullable=False
    )
    owned_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.users.id'),
        index=True,
        nullable=False
    )
    vc_room = db.relationship(
        'VCRoom',
        lazy=False,
        backref=db.backref(
            'zoom_meeting',
            cascade='all, delete-orphan',
            uselist=False,
            lazy=False
        )
    )

    #: The user who owns the Zoom room
    owned_by_user = db.relationship(
        'User',
        lazy=True,
        backref=db.backref(
            'vc_rooms_zoom',
            lazy='dynamic'
        )
    )

    @property
    def join_url(self):
        from indico_vc_zoom.plugin import ZoomPlugin
        url = self.vc_room.data['url']
        return url

    @return_ascii
    def __repr__(self):
        return '<ZoomMeeting({}, {}, {})>'.format(self.vc_room, self.meeting, self.owned_by_user)


@listens_for(ZoomMeeting.owned_by_user, 'set')
def _owned_by_user_set(target, user, *unused):
    if target.vc_room and user.as_principal != tuple(target.vc_room.data['owner']):
        target.vc_room.data['owner'] = user.as_principal
        flag_modified(target.vc_room, 'data')
