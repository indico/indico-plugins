# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re
import sys
import threading
from functools import wraps

from flask import current_app
from flask.globals import _app_ctx_stack

from indico.modules.groups import GroupProxy
from indico.util.caching import memoize_redis


def parallelize(func, entries, batch_size=200):
    @wraps(func)
    def wrapper(*args, **kwargs):
        iterable_lock = threading.Lock()
        result_lock = threading.Lock()
        abort = threading.Event()
        finished = threading.Event()
        results = []
        app = current_app._get_current_object()
        main_app_context = _app_ctx_stack.top
        worker_exc_info = None

        def worker(iterator):
            nonlocal worker_exc_info
            while not abort.is_set() and not finished.is_set():
                try:
                    with iterable_lock:
                        with main_app_context:
                            item = next(iterator)
                except StopIteration:
                    finished.set()
                    break

                with app.app_context():
                    try:
                        res = func(item, *args, **kwargs)
                    except BaseException:
                        worker_exc_info = sys.exc_info()
                        finished.set()
                        return
                    with result_lock:
                        results.append(res)

        it = iter(entries)
        threads = [threading.Thread(target=worker, name=f'worker/{i}', args=(it,))
                   for i in enumerate(range(batch_size))]

        for t in threads:
            t.start()

        try:
            finished.wait()
        except KeyboardInterrupt:
            print('\nFinishing pending jobs before aborting')
            abort.set()

        for t in threads:
            t.join()

        if worker_exc_info:
            raise worker_exc_info[1].with_traceback(worker_exc_info[2])

        return results, abort.is_set()

    return wrapper


def format_query(query, placeholders):
    """Format and split the query into keywords and placeholders.

    https://cern-search.docs.cern.ch/usage/operations/#advanced-queries

    :param query: search query
    :param placeholders: placeholder whitelist
    :returns escaped query
    """
    patt = r'(?:^|\s)({}):([^:"\s]+|"[^"]+")(?:$|\s)'.format('|'.join(map(re.escape, placeholders)))
    idx = 0
    keys = []
    for match in re.finditer(patt, query):
        placeholder = f'{placeholders[match.group(1)]}:{escape(match.group(2))}'
        if idx != match.start():
            keys.append(escape(query[idx:match.start()]))
        keys.append(placeholder)
        idx = match.end()

    if idx != len(query):
        keys.append(escape(query[idx:len(query)]))

    return ' '.join(keys).strip()


def format_filters(params, filters, range_filters):
    """Extract any special placeholder filter, such as ranges, from the query params.

    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#_ranges

    :param params: The filter query params
    :param filters: The filter whitelist
    :param range_filters: The range filter whitelist
    :returns: filters, extracted placeholders
    """
    _filters = {}
    query = []
    for k, v in params.items():
        if k not in filters:
            continue
        if k in range_filters:
            match = re.match(r'[[{].+ TO .+[]}]', v)
            if match:
                query.append(f'+{range_filters[k]}:{v}')
            continue
        _filters[k] = v
    return _filters, ' '.join(query)


def escape(query):
    """Prepend all special ElasticSearch characters with a backslash."""
    patt = r'([+\-=><!(){}[\]\^~?:\\\/]|&&|\|\|)'
    return re.sub(patt, r'\\\1', query)


def remove_none_entries(obj):
    """Remove dict entries that are ``None``.

    This is cascaded in case of nested dicts/collections.
    """
    if isinstance(obj, dict):
        return {k: remove_none_entries(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, (list, tuple, set)):
        return type(obj)(map(remove_none_entries, obj))
    return obj


@memoize_redis(3600)
def get_user_access(user):
    if not user:
        return []
    access = [user.identifier] + [u.identifier for u in user.get_merged_from_users_recursive()]
    access += [GroupProxy(x.id, _group=x).identifier for x in user.local_groups]
    if user.can_get_all_multipass_groups:
        access += [GroupProxy(x.name, x.provider.name, x).identifier
                   for x in user.iter_all_multipass_groups()]
    return access
