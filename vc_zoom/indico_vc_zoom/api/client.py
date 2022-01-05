# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2022 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import time

import jwt
from pytz import utc
from requests import Session
from requests.exceptions import HTTPError


def format_iso_dt(d):
    """Convert a datetime objects to a UTC-based string.

    :param d: The :class:`datetime.datetime` to convert to a string
    :returns: The string representation of the date
    """
    return d.astimezone(utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _handle_response(resp, expected_code=200, expects_json=True):
    try:
        resp.raise_for_status()
        if resp.status_code != expected_code:
            raise HTTPError(f'Unexpected status code {resp.status_code}', response=resp)
    except HTTPError:
        from indico_vc_zoom.plugin import ZoomPlugin
        ZoomPlugin.logger.error('Error in API call to %s: %s', resp.url, resp.content)
        raise
    return resp.json() if expects_json else resp


class APIException(Exception):
    pass


class BaseComponent:
    def __init__(self, base_uri, config, timeout):
        self.base_uri = base_uri
        self.config = config
        self.timeout = timeout

    @property
    def token(self):
        header = {'alg': 'HS256', 'typ': 'JWT'}
        payload = {'iss': self.config['api_key'], 'exp': int(time.time() + 3600)}
        return jwt.encode(payload, self.config['api_secret'], algorithm='HS256', headers=header)

    @property
    def session(self):
        session = Session()
        session.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        return session


class MeetingComponent(BaseComponent):
    def list(self, user_id, **kwargs):
        return self.get(
            f'{self.base_uri}/users/{user_id}/meetings', params=kwargs
        )

    def create(self, user_id, **kwargs):
        if kwargs.get('start_time'):
            kwargs['start_time'] = format_iso_dt(kwargs['start_time'])
        return self.session.post(
            f'{self.base_uri}/users/{user_id}/meetings',
            json=kwargs
        )

    def get(self, meeting_id, **kwargs):
        return self.session.get(f'{self.base_uri}/meetings/{meeting_id}', json=kwargs)

    def update(self, meeting_id, **kwargs):
        if kwargs.get('start_time'):
            kwargs['start_time'] = format_iso_dt(kwargs['start_time'])
        return self.session.patch(
            f'{self.base_uri}/meetings/{meeting_id}', json=kwargs
        )

    def delete(self, meeting_id, **kwargs):
        return self.session.delete(
            f'{self.base_uri}/meetings/{meeting_id}', json=kwargs
        )


class WebinarComponent(BaseComponent):
    def list(self, user_id, **kwargs):
        return self.get(
            f'{self.base_uri}/users/{user_id}/webinars', params=kwargs
        )

    def create(self, user_id, **kwargs):
        if kwargs.get('start_time'):
            kwargs['start_time'] = format_iso_dt(kwargs['start_time'])
        return self.session.post(
            f'{self.base_uri}/users/{user_id}/webinars',
            json=kwargs
        )

    def get(self, meeting_id, **kwargs):
        return self.session.get(f'{self.base_uri}/webinars/{meeting_id}', json=kwargs)

    def update(self, meeting_id, **kwargs):
        if kwargs.get('start_time'):
            kwargs['start_time'] = format_iso_dt(kwargs['start_time'])
        return self.session.patch(
            f'{self.base_uri}/webinars/{meeting_id}', json=kwargs
        )

    def delete(self, meeting_id, **kwargs):
        return self.session.delete(
            f'{self.base_uri}/webinars/{meeting_id}', json=kwargs
        )


class UserComponent(BaseComponent):
    def me(self):
        return self.get('me')

    def list(self, **kwargs):
        return self.session.get(f'{self.base_uri}/users', params=kwargs)

    def create(self, **kwargs):
        return self.session.post(f'{self.base_uri}/users', params=kwargs)

    def update(self, user_id, **kwargs):
        return self.session.patch(f'{self.base_uri}/users/{user_id}', params=kwargs)

    def delete(self, user_id, **kwargs):
        return self.session.delete(f'{self.base_uri}/users/{user_id}', params=kwargs)

    def get(self, user_id, **kwargs):
        return self.session.get(f'{self.base_uri}/users/{user_id}', params=kwargs)


class ZoomClient:
    """Zoom REST API Python Client."""

    BASE_URI = 'https://api.zoom.us/v2'

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
        # Setup the config details
        config = {
            'api_key': api_key,
            'api_secret': api_secret
        }

        # Instantiate the components
        self.components = {
            key: component(base_uri=self.BASE_URI, config=config, timeout=timeout)
            for key, component in self._components.items()
        }

    @property
    def meeting(self):
        """Get the meeting component."""
        return self.components['meeting']

    @property
    def user(self):
        """Get the user component."""
        return self.components['user']

    @property
    def webinar(self):
        """Get the webinar component."""
        return self.components['webinar']


class ZoomIndicoClient:
    def __init__(self):
        from indico_vc_zoom.plugin import ZoomPlugin
        self.client = ZoomClient(
            ZoomPlugin.settings.get('api_key'),
            ZoomPlugin.settings.get('api_secret')
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

    def get_user(self, user_id, silent=False):
        resp = self.client.user.get(user_id)
        if resp.status_code == 404 and silent:
            return None
        return _handle_response(resp)
