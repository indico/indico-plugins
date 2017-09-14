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

from indico.core.db.sqlalchemy import UTCDateTime, db
from indico.util.date_time import now_utc
from indico.util.string import return_ascii

from indico_chat.xmpp import delete_room


class Chatroom(db.Model):
    __tablename__ = 'chatrooms'
    __table_args__ = (db.UniqueConstraint('jid_node', 'custom_server'),
                      {'schema': 'plugin_chat'})

    #: Chatroom ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    #: Node of the chatroom's JID (the part before `@domain`)
    jid_node = db.Column(
        db.String,
        nullable=False
    )
    #: Name of the chatroom
    name = db.Column(
        db.String,
        nullable=False
    )
    #: Description of the chatroom
    description = db.Column(
        db.Text,
        nullable=False,
        default=''
    )
    #: Password to join the room
    password = db.Column(
        db.String,
        nullable=False,
        default=''
    )
    #: Custom Jabber MUC server hostname
    custom_server = db.Column(
        db.String,
        nullable=False,
        default=''
    )
    #: ID of the creator
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.users.id'),
        index=True,
        nullable=False
    )
    #: Creation timestamp of the chatroom
    created_dt = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )
    #: Modification timestamp of the chatroom
    modified_dt = db.Column(
        UTCDateTime
    )

    #: The user who created the chatroom
    created_by_user = db.relationship(
        'User',
        lazy=True,
        backref=db.backref(
            'chatrooms',
            lazy='dynamic'
        )
    )

    @property
    def locator(self):
        return {'chatroom_id': self.id}

    @property
    def server(self):
        """The server name of the chatroom.

        Usually the default one unless a custom one is set.
        """
        from indico_chat.plugin import ChatPlugin

        return self.custom_server or ChatPlugin.settings.get('muc_server')

    @property
    def jid(self):
        return '{}@{}'.format(self.jid_node, self.server)

    @return_ascii
    def __repr__(self):
        server = self.server
        if self.custom_server:
            server = '!' + server
        return '<Chatroom({}, {}, {}, {})>'.format(self.id, self.name, self.jid_node, server)


class ChatroomEventAssociation(db.Model):
    __tablename__ = 'chatroom_events'
    __table_args__ = {'schema': 'plugin_chat'}

    #: ID of the event
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('events.events.id'),
        primary_key=True,
        index=True,
        autoincrement=False
    )
    #: ID of the chatroom
    chatroom_id = db.Column(
        db.Integer,
        db.ForeignKey('plugin_chat.chatrooms.id'),
        primary_key=True,
        index=True
    )
    #: If the chatroom should be hidden on the event page
    hidden = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    #: If the password should be visible on the event page
    show_password = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    #: The associated :class:Chatroom
    chatroom = db.relationship(
        'Chatroom',
        lazy=False,
        backref=db.backref('events', cascade='all, delete-orphan')
    )
    #: The associated event
    event = db.relationship(
        'Event',
        lazy=True,
        backref=db.backref(
            'chatroom_associations',
            lazy='dynamic'
        )
    )

    @property
    def locator(self):
        return dict(self.chatroom.locator, confId=self.event_id)

    @return_ascii
    def __repr__(self):
        return '<ChatroomEventAssociation({}, {})>'.format(self.event_id, self.chatroom)

    @classmethod
    def find_for_event(cls, event, include_hidden=False, **kwargs):
        """Returns a Query that retrieves the chatrooms for an event

        :param event: an indico event (with a numeric ID)
        :param include_hidden: if hidden chatrooms should be included, too
        :param kwargs: extra kwargs to pass to ``find()``
        """
        query = cls.find(event_id=event.id, **kwargs)
        if not include_hidden:
            query = query.filter(~cls.hidden)
        return query

    def delete(self, reason=''):
        """Deletes the event chatroom and if necessary the chatroom, too.

        :param reason: reason for the deletion
        :return: True if the associated chatroom was also
                 deleted, otherwise False
        """
        db.session.delete(self)
        db.session.flush()
        if not self.chatroom.events:
            db.session.delete(self.chatroom)
            db.session.flush()
            delete_room(self.chatroom, reason)
            return True
        return False
