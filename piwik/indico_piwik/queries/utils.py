import json

from flask_pluginengine import current_plugin


def get_json_from_remote_server(func, default={}, **kwargs):
    """
    Safely manage calls to the remote server by encapsulating JSON creation
    from Piwik data.
    """
    try:
        rawjson = func(kwargs)
        return json.loads(rawjson)
    except Exception:
        current_plugin.get_logger().exception('Unable to load JSON from source {}'.format(str(rawjson)))
        return default


def reduce_json(data):
    """Reduce a JSON object."""
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
