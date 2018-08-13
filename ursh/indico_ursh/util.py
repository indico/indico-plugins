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

import requests
from werkzeug.exceptions import ServiceUnavailable


def request_short_url(original_url):
    from indico_ursh.plugin import UrshPlugin
    api_key = UrshPlugin.settings.get('api_key')
    api_host = UrshPlugin.settings.get('api_host')

    if not api_key or not api_host:
        raise ServiceUnavailable('Not configured')

    headers = {'Authorization': 'Bearer {api_key}'.format(api_key=api_key)}
    response = requests.post(api_host, data=dict(url=original_url, allow_reuse=True), headers=headers)
    response.raise_for_status()

    data = response.json()
    return data['short_url']
