from __future__ import unicode_literals

import random
import string

from requests.exceptions import HTTPError

from indico.core.db import db
from indico.modules.users.models.emails import UserEmail
from indico.modules.users.models.users import User
from indico.modules.vc.exceptions import VCRoomError, VCRoomNotFoundError
from indico.util.date_time import now_utc

from indico_vc_zoom import _
from indico_vc_zoom.api import ZoomIndicoClient


def find_enterprise_email(user):
    """Find a user's first e-mail address which can be used by the Zoom API.

    :param user: the `User` in question
    :return: the e-mail address if it exists, otherwise `None`
    """
    from indico_vc_zoom.plugin import ZoomPlugin
    providers = [auth.strip() for auth in ZoomPlugin.settings.get('email_domains').split(',')]
    result = UserEmail.query.filter(
        UserEmail.user == user,
        ~User.is_blocked,
        ~User.is_deleted,
        db.or_(UserEmail.email.ilike("%%@{}".format(provider)) for provider in providers)
    ).join(User).first()
    return result.email if result else None


def gen_random_password():
    """Generate a random 10-character-long alphanumeric string."""
    return ''.join(random.sample(string.ascii_lowercase + string.ascii_uppercase + string.digits, 10))


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
            raise VCRoomNotFoundError(_("This room has been deleted from Zoom"))
        else:
            from indico_vc_zoom.plugin import ZoomPlugin
            ZoomPlugin.logger.exception('Error getting Zoom Room: %s', e.response.content)
            raise VCRoomError(_("Problem fetching room from Zoom. Please contact support if the error persists."))


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
