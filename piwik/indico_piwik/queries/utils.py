# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
