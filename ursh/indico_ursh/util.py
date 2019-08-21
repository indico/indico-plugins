# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import json
import posixpath

import requests
from werkzeug.exceptions import ServiceUnavailable


def _get_settings():
    from indico_ursh.plugin import UrshPlugin
    api_key = UrshPlugin.settings.get('api_key')
    api_host = UrshPlugin.settings.get('api_host')

    if not api_key or not api_host:
        raise ServiceUnavailable('Not configured')

    return api_key, api_host


def is_configured():
    """Check whether the plugin is properly configured."""
    from indico_ursh.plugin import UrshPlugin
    api_key = UrshPlugin.settings.get('api_key')
    api_host = UrshPlugin.settings.get('api_host')
    return bool(api_key and api_host)


def request_short_url(original_url):
    from indico_ursh.plugin import UrshPlugin
    api_key, api_host = _get_settings()
    headers = {'Authorization': 'Bearer {api_key}'.format(api_key=api_key), 'Content-Type': 'application/json'}
    url = posixpath.join(api_host, 'api/urls/')

    response = requests.post(url, data=json.dumps({'url': original_url, 'allow_reuse': True}), headers=headers)
    response.raise_for_status()
    data = response.json()
    UrshPlugin.logger.info('Shortcut created: %s -> %s', data['shortcut'], original_url)
    return data['short_url']


def register_shortcut(original_url, shortcut, user):
    from indico_ursh.plugin import UrshPlugin
    api_key, api_host = _get_settings()
    headers = {'Authorization': 'Bearer {api_key}'.format(api_key=api_key), 'Content-Type': 'application/json'}
    url = posixpath.join(api_host, 'api/urls', shortcut)
    data = {'url': original_url, 'allow_reuse': True, 'meta': {'indico.user': user.id}}

    response = requests.put(url, data=json.dumps(data), headers=headers)
    if not (400 <= response.status_code < 500):
        response.raise_for_status()

    data = response.json()
    if not data.get('error'):
        UrshPlugin.logger.info('Shortcut created: %s -> %s', data['shortcut'], original_url)
    return data


def strip_end(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:len(text) - len(suffix)]
