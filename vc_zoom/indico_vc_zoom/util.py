# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools
import random
import re
import string

from requests.exceptions import HTTPError

from indico.core.db import db
from indico.modules.auth.models.identities import Identity
from indico.modules.users.models.emails import UserEmail
from indico.modules.users.models.users import User
from indico.modules.users.util import get_user_by_email
from indico.modules.vc.exceptions import VCRoomError, VCRoomNotFoundError
from indico.util.caching import memoize_request
from indico.util.date_time import now_utc
from indico.util.enum import IndicoEnum, RichEnum
from indico.util.user import principal_from_identifier

from indico_vc_zoom import _
from indico_vc_zoom.api import ZoomIndicoClient


class ZoomMeetingType(int, IndicoEnum):
    instant_meeting = 1
    scheduled_meeting = 2
    recurring_meeting_no_time = 3
    recurring_meeting_fixed_time = 8
    pmi_meeting = 4
    webinar = 5
    recurring_webinar_no_time = 6
    recurring_webinar_fixed_time = 9


class UserLookupMode(str, RichEnum):
    __titles__ = {
        'all_emails': _('All emails'),
        'email_domains': _('Email domains'),
        'authenticators': _('Authenticators'),
    }

    @property
    def title(self):
        return RichEnum.title.__get__(self, type(self))

    all_emails = 'all_emails'
    email_domains = 'email_domains'
    authenticators = 'authenticators'


def _iter_user_identifiers(user):
    """Iterates over all existing user identifiers that can be used with Zoom"""
    from indico_vc_zoom.plugin import ZoomPlugin
    done = set()
    for provider in ZoomPlugin.settings.get('authenticators'):
        for __, identifier in user.iter_identifiers(check_providers=True, providers={provider}):
            if identifier in done:
                continue
            done.add(identifier)
            yield identifier


def iter_user_emails(user):
    """Yield all emails of a user that may work with zoom.

    :param user: the `User` in question
    """
    from indico_vc_zoom.plugin import ZoomPlugin
    mode = ZoomPlugin.settings.get('user_lookup_mode')
    if mode in (UserLookupMode.all_emails, UserLookupMode.email_domains):
        email_criterion = True
        if mode == UserLookupMode.email_domains:
            domains = ZoomPlugin.settings.get('email_domains')
            if not domains:
                return
            email_criterion = db.or_(UserEmail.email.endswith(f'@{domain}') for domain in domains)
        # get all matching e-mails, primary first
        query = UserEmail.query.filter(
            UserEmail.user == user,
            ~User.is_blocked,
            ~User.is_deleted,
            email_criterion
        ).join(User).order_by(UserEmail.is_primary.desc())
        for entry in query:
            yield entry.email
    elif mode == UserLookupMode.authenticators:
        domain = ZoomPlugin.settings.get('enterprise_domain')
        for username in _iter_user_identifiers(user):
            yield f'{username}@{domain}'


@memoize_request
def find_enterprise_email(user):
    """Get the email address of a user that has a zoom account."""
    client = ZoomIndicoClient()
    return next((email for email in iter_user_emails(user) if client.get_user(email, silent=True)), None)


def gen_random_password():
    """Generate a random 8-character-long numeric string."""
    return ''.join(random.choice(string.digits) for _ in range(8))


def fetch_zoom_meeting(vc_room, client=None, is_webinar=False):
    """Fetch a Zoom meeting from the Zoom API.

    :param vc_room: The `VCRoom` object
    :param client: a `ZoomIndicoClient` object, otherwise a fresh one will be created
    :param is_webinar: whether the call concerns a webinar (used to call the correct endpoint)
    """
    try:
        client = client or ZoomIndicoClient()
        if is_webinar:
            return client.get_webinar(vc_room.data['zoom_id'])
        return client.get_meeting(vc_room.data['zoom_id'])
    except HTTPError as e:
        if e.response.status_code in {400, 404}:
            # Indico will automatically mark this room as deleted
            raise VCRoomNotFoundError(_('This room has been deleted from Zoom'))
        else:
            from indico_vc_zoom.plugin import ZoomPlugin
            ZoomPlugin.logger.exception('Error getting Zoom Room: %s', e.response.content)
            raise VCRoomError(_('Problem fetching room from Zoom. Please contact support if the error persists.'))


def update_zoom_meeting(zoom_id, changes, is_webinar=False):
    """Update a meeting which already exists in the Zoom API.

    :param zoom_id: ID of the meeting
    :param changes: dictionary with new attribute values
    :param is_webinar: whether the call concerns a webinar (used to call the correct endpoint)
    """
    client = ZoomIndicoClient()
    try:
        if is_webinar:
            client.update_webinar(zoom_id, changes)
        else:
            client.update_meeting(zoom_id, changes)
    except HTTPError as e:
        from indico_vc_zoom.plugin import ZoomPlugin
        ZoomPlugin.logger.exception("Error updating meeting '%s': %s", zoom_id, e.response.content)

        if e.response.json()['code'] == 3001:
            # "Meeting does not exist"
            raise VCRoomNotFoundError(_('Room no longer exists in Zoom'))

        raise VCRoomError(_("Can't update meeting. Please contact support if the error persists."))


def get_schedule_args(obj):
    """Create a dictionary with scheduling information from an Event/Contribution/SessionBlock.

    :param obj: An `Event`, `Contribution` or `SessionBlock`
    """
    duration = obj.end_dt - obj.start_dt

    if obj.start_dt < now_utc():
        return {}

    return {
        'start_time': obj.start_dt,
        'duration': duration.total_seconds() / 60,
    }


def get_url_data_args(url):
    """Create a dictionary with proper public/private "join URL" fields.""

    :param url: the original URL
    """
    return {
        'url': url,
        'public_url': url.split('?')[0],
    }


def process_alternative_hosts(emails):
    """Convert a comma-concatenated list of alternative host e-mails into a list of identifiers."""
    from indico_vc_zoom.plugin import ZoomPlugin
    mode = ZoomPlugin.settings.get('user_lookup_mode')
    emails = re.findall(r'[^,;]+', emails)
    if mode in (UserLookupMode.all_emails, UserLookupMode.email_domains):
        users = {get_user_by_email(email) for email in emails}
    elif mode == UserLookupMode.authenticators:
        users = set()
        domain = ZoomPlugin.settings.get('enterprise_domain')
        usernames = {email.split('@')[0] for email in emails if email.endswith(f'@{domain}')}
        providers = ZoomPlugin.settings.get('authenticators')
        users = []
        if providers and usernames:
            criteria = db.or_(((Identity.provider == provider) & (Identity.identifier == username))
                              for provider, username in itertools.product(providers, usernames))
            users = [identity.user for identity in Identity.query.filter(criteria)]
    else:
        raise TypeError('invalid mode')
    return [u.identifier for u in users if u is not None]


def get_alt_host_emails(identifiers):
    """Convert a list of identities into a list of enterprise e-mails."""
    emails = [find_enterprise_email(principal_from_identifier(ident)) for ident in identifiers]
    if None in emails:
        raise VCRoomError(_('Could not find Zoom user for alternative host'))
    return emails
