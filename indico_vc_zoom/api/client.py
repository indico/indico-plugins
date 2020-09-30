from __future__ import absolute_import, unicode_literals

import time

import jwt
from requests import Session
from requests.exceptions import HTTPError
from pytz import utc


def format_iso_dt(d):
    """Convertdatetime objects to a UTC-based string.

    :param d: The :class:`datetime.datetime` to convert to a string
    :returns: The string representation of the date
    """
    return d.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _handle_response(resp, expected_code=200, expects_json=True):
    resp.raise_for_status()
    if resp.status_code != expected_code:
        raise HTTPError("Unexpected status code {}".format(resp.status_code), response=resp)
    if expects_json:
        return resp.json()
    else:
        return resp


class APIException(Exception):
    pass


class BaseComponent(object):
    def __init__(self, base_uri, config, timeout):
        self.base_uri = base_uri
        self.config = config
        self.timeout = timeout

    @property
    def token(self):
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"iss": self.config['api_key'], "exp": int(time.time() + 3600)}
        token = jwt.encode(payload, self.config['api_secret'], algorithm="HS256", headers=header)
        return token.decode("utf-8")

    @property
    def session(self):
        session = Session()
        session.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(self.token)
        }
        return session


class MeetingComponent(BaseComponent):
    def list(self, user_id, **kwargs):
        return self.get(
            "{}/users/{}/meetings".format(self.base_uri, user_id), params=kwargs
        )

    def create(self, user_id, **kwargs):
        if kwargs.get("start_time"):
            kwargs["start_time"] = format_iso_dt(kwargs["start_time"])
        return self.session.post(
            "{}/users/{}/meetings".format(self.base_uri, user_id),
            json=kwargs
        )

    def get(self, meeting_id, **kwargs):
        return self.session.get("{}/meetings/{}".format(self.base_uri, meeting_id), json=kwargs)

    def update(self, meeting_id, **kwargs):
        if kwargs.get("start_time"):
            kwargs["start_time"] = format_iso_dt(kwargs["start_time"])
        return self.session.patch(
            "{}/meetings/{}".format(self.base_uri, meeting_id), json=kwargs
        )

    def delete(self, meeting_id, **kwargs):
        return self.session.delete(
            "{}/meetings/{}".format(self.base_uri, meeting_id), json=kwargs
        )


class WebinarComponent(BaseComponent):
    def list(self, user_id, **kwargs):
        return self.get(
            "{}/users/{}/webinars".format(self.base_uri, user_id), params=kwargs
        )

    def create(self, user_id, **kwargs):
        if kwargs.get("start_time"):
            kwargs["start_time"] = format_iso_dt(kwargs["start_time"])
        return self.session.post(
            "{}/users/{}/webinars".format(self.base_uri, user_id),
            json=kwargs
        )

    def get(self, meeting_id, **kwargs):
        return self.session.get("{}/webinars/{}".format(self.base_uri, meeting_id), json=kwargs)

    def update(self, meeting_id, **kwargs):
        if kwargs.get("start_time"):
            kwargs["start_time"] = format_iso_dt(kwargs["start_time"])
        return self.session.patch(
            "{}/webinars/{}".format(self.base_uri, meeting_id), json=kwargs
        )

    def delete(self, meeting_id, **kwargs):
        return self.session.delete(
            "{}/webinars/{}".format(self.base_uri, meeting_id), json=kwargs
        )


class UserComponent(BaseComponent):
    def me(self):
        return self.get('me')

    def list(self, **kwargs):
        return self.session.get("{}/users".format(self.base_uri), params=kwargs)

    def create(self, **kwargs):
        return self.session.post("{}/users".format(self.base_uri), params=kwargs)

    def update(self, user_id, **kwargs):
        return self.session.patch("{}/users/{}".format(self.base_uri, user_id), params=kwargs)

    def delete(self, user_id, **kwargs):
        return self.session.delete("{}/users/{}".format(self.base_uri, user_id), params=kwargs)

    def add_assistant(self, user_id, **kwargs):
        return self.session.post("{}/users/{}/assistants".format(self.base_uri, user_id), json=kwargs)

    def get_assistants(self, user_id, **kwargs):
        return self.session.get("{}/users/{}/assistants".format(self.base_uri, user_id), params=kwargs)

    def get(self, user_id, **kwargs):
        return self.session.get("{}/users/{}".format(self.base_uri, user_id), params=kwargs)


class ZoomClient(object):
    """Zoom REST API Python Client."""

    _components = {
        'user': UserComponent,
        'meeting': MeetingComponent,
        'webinar': WebinarComponent
    }

    def __init__(self, api_key, api_secret, timeout=15):
        """Create a new Zoom client.

        :param api_key: the Zoom JWT API key
        :param api_secret: the Zoom JWT API Secret
        :param timeout: the time out to use for API requests
        """
        BASE_URI = "https://api.zoom.us/v2"

        # Setup the config details
        config = {
            "api_key": api_key,
            "api_secret": api_secret
        }

        # Instantiate the components

        self.components = {
            key: component(base_uri=BASE_URI, config=config, timeout=timeout)
            for key, component in self._components.viewitems()
        }

    @property
    def meeting(self):
        """Get the meeting component."""
        return self.components.get("meeting")

    @property
    def user(self):
        """Get the user component."""
        return self.components.get("user")

    @property
    def webinar(self):
        """Get the user component."""
        return self.components.get("webinar")


class ZoomIndicoClient(object):
    def __init__(self):
        self._refresh_client()

    def _refresh_client(self):
        from indico_vc_zoom.plugin import ZoomPlugin
        settings = ZoomPlugin.settings
        self.client = ZoomClient(
            settings.get('api_key'),
            settings.get('api_secret')
        )

    def create_meeting(self, user_id, **kwargs):
        return _handle_response(self.client.meeting.create(user_id, **kwargs), 201)

    def get_meeting(self, meeting_id):
        return _handle_response(self.client.meeting.get(meeting_id))

    def update_meeting(self, meeting_id, data):
        return _handle_response(self.client.meeting.update(meeting_id, **data), 204, expects_json=False)

    def delete_meeting(self, meeting_id):
        return _handle_response(self.client.meeting.delete(meeting_id), 204, expects_json=False)

    def create_webinar(self, user_id, **kwargs):
        return _handle_response(self.client.webinar.create(user_id, **kwargs), 201)

    def get_webinar(self, webinar_id):
        return _handle_response(self.client.webinar.get(webinar_id))

    def update_webinar(self, webinar_id, data):
        return _handle_response(self.client.webinar.update(webinar_id, **data), 204, expects_json=False)

    def delete_webinar(self, webinar_id):
        return _handle_response(self.client.webinar.delete(webinar_id), 204, expects_json=False)

    def check_user_meeting_time(self, user_id, start_dt, end_dt):
        pass

    def get_user(self, user_id):
        return _handle_response(self.client.user.get(user_id))

    def get_assistants_for_user(self, user_id):
        return _handle_response(self.client.user.get_assistants(user_id))

    def add_assistant_to_user(self, user_id, assistant_email):
        return _handle_response(self.client.user.add_assistant(user_id, assistants=[{'email': assistant_email}]), 201)
