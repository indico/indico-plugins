# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

import json

from flask_pluginengine import current_plugin


def get_json_from_remote_server(func, **kwargs):
    """
    Safely manage calls to the remote server by encapsulating JSON creation
    from Piwik data.
    """
    rawjson = func(**kwargs)
    if rawjson is None:
        # If the request failed we already logged in in PiwikRequest;
        # no need to get into the exception handler below.
        return {}
    try:
        data = json.loads(rawjson)
        if isinstance(data, dict) and data.get('result') == 'error':
            current_plugin.logger.error('The Piwik server responded with an error: %s', data['message'])
            return {}
        return data
    except Exception:
        current_plugin.logger.exception('Unable to load JSON from source %s', rawjson)
        return {}


def reduce_json(data):
    """Reduce a JSON object"""
    return reduce(lambda x, y: int(x) + int(y), data.values())


def stringify_seconds(seconds=0):
    """
    Takes time as a value of seconds and deduces the delta in human-readable
    HHh MMm SSs format.
    """
    seconds = int(seconds)
    minutes = seconds / 60
    ti = {'h': 0, 'm': 0, 's': 0}

    if seconds > 0:
        ti['s'] = seconds % 60
        ti['m'] = minutes % 60
        ti['h'] = minutes / 60

    return "%dh %dm %ds" % (ti['h'], ti['m'], ti['s'])
