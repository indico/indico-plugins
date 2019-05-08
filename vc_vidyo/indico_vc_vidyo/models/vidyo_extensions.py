# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import urllib

from sqlalchemy.event import listens_for
from sqlalchemy.orm.attributes import flag_modified

from indico.core.db.sqlalchemy import db
from indico.util.string import return_ascii


class VidyoExtension(db.Model):
    __tablename__ = 'vidyo_extensions'
    __table_args__ = {'schema': 'plugin_vc_vidyo'}

    #: ID of the videoconference room
    vc_room_id = db.Column(
        db.Integer,
        db.ForeignKey('events.vc_rooms.id'),
        primary_key=True
    )
    extension = db.Column(
        db.BigInteger,
        index=True
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
            'vidyo_extension',
            cascade='all, delete-orphan',
            uselist=False,
            lazy=False
        )
    )

    #: The user who owns the Vidyo room
    owned_by_user = db.relationship(
        'User',
        lazy=True,
        backref=db.backref(
            'vc_rooms_vidyo',
            lazy='dynamic'
        )
    )

    @property
    def join_url(self):
        from indico_vc_vidyo.plugin import VidyoPlugin
        url = self.vc_room.data['url']
        custom_url_tpl = VidyoPlugin.settings.get('client_chooser_url')
        if custom_url_tpl:
            return custom_url_tpl + '?' + urllib.urlencode({'url': url})
        return url

    @return_ascii
    def __repr__(self):
        return '<VidyoExtension({}, {}, {})>'.format(self.vc_room, self.extension, self.owned_by_user)


@listens_for(VidyoExtension.owned_by_user, 'set')
def _owned_by_user_set(target, user, *unused):
    if target.vc_room and user.as_principal != tuple(target.vc_room.data['owner']):
        target.vc_room.data['owner'] = user.as_principal
        flag_modified(target.vc_room, 'data')
