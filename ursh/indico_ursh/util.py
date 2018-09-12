# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
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


def request_short_url(original_url):
    api_key, api_host = _get_settings()
    headers = {'Authorization': 'Bearer {api_key}'.format(api_key=api_key)}

    response = requests.post(api_host, data=dict(url=original_url, allow_reuse=True), headers=headers)
    if response.status_code not in (400, ):
        response.raise_for_status()

    data = response.json()
    return data.get('short_url')


def register_shortcut(original_url, shortcut):
    api_key, api_host = _get_settings()
    headers = {'Authorization': 'Bearer {api_key}'.format(api_key=api_key)}

    # ursh expects shortcut as a path argument
    api_host = posixpath.join(api_host, shortcut)

    response = requests.put(api_host, data=dict(url=original_url), headers=headers)
    if response.status_code not in (403, ):
        response.raise_for_status()

    data = response.json()
    return data


def strip_end(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:len(text)-len(suffix)]
