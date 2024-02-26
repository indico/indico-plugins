# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2024 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import time

import requests
from pytz import utc
from requests import Session
from requests.exceptions import HTTPError

from indico.core.cache import make_scoped_cache
from indico.util.string import crc32


token_cache = make_scoped_cache('zoom-api-token')


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


class ZoomSession(Session):
    def __init__(self, zoom_plugin_config):
        super().__init__()
        self.__zoom_plugin_config = zoom_plugin_config
        self.__set_zoom_headers(self.__get_token())

    def __get_token(self, *, force=False):
        return get_zoom_token(self.__zoom_plugin_config, force=force)[0]

    def __set_zoom_headers(self, token):
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    def request(self, *args, **kwargs):
        from indico_vc_zoom.plugin import ZoomPlugin
        resp = super().request(*args, **kwargs)
        if resp.status_code == 401:
            ZoomPlugin.logger.warn('Request failed with invalid token; getting a new one')
            self.__set_zoom_headers(self.__get_token(force=True))
            resp = super().request(*args, **kwargs)
        return resp


class BaseComponent:
    def __init__(self, base_uri, config, timeout):
        self.base_uri = base_uri
        self.config = config
        self.timeout = timeout

    @property
    def session(self):
        return ZoomSession(self.config)


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

    def __init__(self, account_id, client_id, client_secret, timeout=15):
        """Create a new Zoom client.

        :param account_id: the Zoom Server OAuth Account ID
        :param client_id: the Zoom Server OAuth Client ID
        :param client_secret: the Zoom Server OAuth Client Secret
        :param timeout: the time out to use for API requests
        """
        # Setup the config details
        config = {
            'account_id': account_id,
            'client_id': client_id,
            'client_secret': client_secret,
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
            ZoomPlugin.settings.get('account_id'),
            ZoomPlugin.settings.get('client_id'),
            ZoomPlugin.settings.get('client_secret'),
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


def get_zoom_token(config, *, force=False):
    from indico_vc_zoom.plugin import ZoomPlugin

    account_id = config['account_id']
    client_id = config['client_id']
    client_secret = config['client_secret']

    if not (account_id and client_id and client_secret):
        raise Exception('Zoom authentication not configured')

    ZoomPlugin.logger.debug(f'Using Server-to-Server-OAuth ({force=})')
    hash_key = '-'.join((account_id, client_id, client_secret))
    cache_key = f'token-{crc32(hash_key)}'
    if not force and (token_data := token_cache.get(cache_key)):
        expires_in = int(token_data['expires_at'] - time.time())
        ZoomPlugin.logger.debug('Using token from cache (%s, %ds remaining)', cache_key, expires_in)
        return token_data['access_token'], token_data['expires_at']
    try:
        resp = requests.post(
            'https://zoom.us/oauth/token',
            params={'grant_type': 'account_credentials', 'account_id': account_id},
            auth=(client_id, client_secret)
        )
        resp.raise_for_status()
    except HTTPError as exc:
        ZoomPlugin.logger.error('Could not get zoom token: %s', exc.response.text if exc.response else exc)
        raise Exception('Could not get zoom token; please contact an admin if this problem persists.')
    token_data = resp.json()
    assert 'access_token' in token_data
    ZoomPlugin.logger.debug('Got new token from Zoom (expires_in=%s, scope=%s)', token_data['expires_in'],
                            token_data['scope'])
    expires_at = int(time.time() + token_data['expires_in'])
    token_data.setdefault('expires_at', expires_at)  # zoom doesn't include this. wtf.
    token_cache.set(cache_key, token_data, token_data['expires_in'])
    return token_data['access_token'], token_data['expires_at']
