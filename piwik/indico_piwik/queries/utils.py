# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import json
from datetime import timedelta
from functools import reduce

from flask_pluginengine import current_plugin

from indico.util.date_time import format_human_timedelta


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
    return reduce(lambda x, y: int(x) + int(y), list(data.values()))


def stringify_seconds(seconds):
    """Format seconds in a compact HHh MMm SSs format."""
    return format_human_timedelta(timedelta(seconds=seconds), narrow=True)
