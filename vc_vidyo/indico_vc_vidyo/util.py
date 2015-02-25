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

from indico.util.user import retrieve_principals, principal_to_tuple
from indico.core.config import Config

from MaKaC.authentication.AuthenticationMgr import AuthenticatorMgr


def get_auth_users():
    """Returns a list of authorized users

    :return: list of Avatar/Group objects
    """
    from indico_vc_vidyo.plugin import VidyoPlugin
    return retrieve_principals(VidyoPlugin.settings.get('authorized_users'))


def is_auth_user(user):
    """Checks if a user is authorized"""
    return any(principal.containsUser(user) for principal in get_auth_users())


def iter_user_identities(avatar):
    """Iterates over all existing user identities that can be used with Vidyo"""
    from indico_vc_vidyo.plugin import VidyoPlugin

    authenticators = (a.strip() for a in VidyoPlugin.settings.get('authenticators').split(','))
    return (identity.getLogin()
            for auth in authenticators
            for identity in avatar.getIdentityByAuthenticatorId(auth))


def get_avatar_from_identity(settings, identity):
    """Get an actual avatar object from an auth identity"""
    authenticators = list(auth.strip() for auth in settings.get('authenticators').split(','))
    return next((avatar for auth_id, avatar in AuthenticatorMgr().getAvatarByLogin(identity, authenticators).iteritems()
                if avatar is not None), None)


def iter_extensions(prefix, event_id):
    """Return extension (prefix + event_id) with an optional suffix which is
       incremented step by step in case of collision
    """
    extension = '{prefix}{event_id}'.format(prefix=prefix, event_id=event_id,)
    yield extension
    suffix = 1
    while True:
        yield '{extension}{suffix}'.format(extension=extension, suffix=suffix)
        suffix += 1


def update_room_from_obj(settings, vc_room, room_obj):
    """Updates a VCRoom DB object using a SOAP room object returned by the API"""
    config = Config.getInstance()

    vc_room.name = room_obj.name

    if room_obj.ownerName != vc_room.data['owner_identity']:
        avatar = get_avatar_from_identity(settings, room_obj.ownerName)
        # if the owner does not exist any more (e.g. was changed on the server),
        # use the janitor user as a placeholder
        vc_room.data['owner'] = (('Avatar', config.getJanitorUserId()) if avatar is None
                                 else principal_to_tuple(avatar))

    vc_room.data.update({
        'description': room_obj.description,
        'vidyo_id': unicode(room_obj.roomID),
        'url': room_obj.RoomMode.roomURL,
        'owner_identity': room_obj.ownerName,
        'room_pin': room_obj.RoomMode.roomPIN if room_obj.RoomMode.hasPIN else "",
        'moderation_pin': room_obj.RoomMode.moderatorPIN if room_obj.RoomMode.hasModeratorPIN else "",
    })
    vc_room.vidyo_extension.value = int(room_obj.extension)
