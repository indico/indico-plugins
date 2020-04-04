

from __future__ import unicode_literals

import re

from flask_multipass import IdentityRetrievalFailed

from indico.core.auth import multipass
from indico.core.db import db
from indico.modules.auth import Identity
from indico.modules.users import User


authenticators_re = re.compile(r'\s*,\s*')


def iter_user_identities(user):
    """Iterates over all existing user identities that can be used with Zoom"""
    from indico_vc_zoom.plugin import ZoomPlugin
    providers = authenticators_re.split(ZoomPlugin.settings.get('authenticators'))
    done = set()
    for provider in providers:
        for _, identifier in user.iter_identifiers(check_providers=True, providers={provider}):
            if identifier in done:
                continue
            done.add(identifier)
            yield identifier


def get_user_from_identifier(settings, identifier):
    """Get an actual User object from an identifier"""
    providers = list(auth.strip() for auth in settings.get('authenticators').split(','))
    identities = Identity.find_all(Identity.provider.in_(providers), Identity.identifier == identifier)
    if identities:
        return sorted(identities, key=lambda x: providers.index(x.provider))[0].user
    for provider in providers:
        try:
            identity_info = multipass.get_identity(provider, identifier)
        except IdentityRetrievalFailed:
            continue
        if identity_info is None:
            continue
        if not identity_info.provider.settings.get('trusted_email'):
            continue
        emails = {email.lower() for email in identity_info.data.getlist('email') if email}
        if not emails:
            continue
        user = User.find_first(~User.is_deleted, User.all_emails.in_(list(emails)))
        if user:
            return user


def iter_extensions(prefix, event_id):
    """Return extension (prefix + event_id) with an optional suffix which is
       incremented step by step in case of collision
    """
    extension = '{prefix}{event_id}'.format(prefix=prefix, event_id=event_id)
    yield extension
    suffix = 1
    while True:
        yield '{extension}{suffix}'.format(extension=extension, suffix=suffix)
        suffix += 1


def update_room_from_obj(settings, vc_room, room_obj):
    """Updates a VCRoom DB object using a SOAP room object returned by the API"""
    vc_room.name = room_obj.name
    if room_obj.ownerName != vc_room.data['owner_identity']:
        owner = get_user_from_identifier(settings, room_obj.ownerName) or User.get_system_user()
        vc_room.zoom_meeting.owned_by_user = owner

    vc_room.data.update({
        'description': room_obj.description,
        'zoom_id': unicode(room_obj.roomID),
        'url': room_obj.RoomMode.roomURL,
        'owner_identity': room_obj.ownerName,
        'room_pin': room_obj.RoomMode.roomPIN if room_obj.RoomMode.hasPIN else "",
        'moderation_pin': room_obj.RoomMode.moderatorPIN if room_obj.RoomMode.hasModeratorPIN else "",
    })
    vc_room.zoom_meeting.extension = int(room_obj.extension)


def retrieve_principal(principal):
    from indico.modules.users import User
    type_, id_ = principal
    if type_ in {'Avatar', 'User'}:
        return User.get(int(id_))
    else:
        raise ValueError('Unexpected type: {}'.format(type_))
