# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re
import threading
from functools import wraps

from flask import current_app
from flask.globals import _app_ctx_stack


def parallelize(func, entries, batch_size=200):
    @wraps(func)
    def wrapper(*args, **kwargs):
        iterable_lock = threading.Lock()
        result_lock = threading.Lock()
        abort = threading.Event()
        results = []
        app = current_app._get_current_object()
        main_app_context = _app_ctx_stack.top

        def worker(iterator):
            while not abort.is_set():
                try:
                    with iterable_lock:
                        with main_app_context:
                            item = next(iterator)
                except StopIteration:
                    break

                with app.app_context():
                    res = func(item, *args, **kwargs)
                    with result_lock:
                        results.append(res)

        it = iter(entries)
        threads = [threading.Thread(target=worker, name=f'worker/{i}', args=(it,))
                   for i in enumerate(range(batch_size))]

        for t in threads:
            t.start()

        for t in threads:
            try:
                t.join()
            except KeyboardInterrupt:
                print('\nFinishing pending jobs before aborting')
                abort.set()
                t.join()
                continue

        return results, abort.is_set()

    return wrapper


def format_query(query, placeholders):
    """Format and split the query into keywords and placeholders.

    https://cern-search.docs.cern.ch/usage/operations/#advanced-queries

    :param query: search query
    :param placeholders: placeholder whitelist
    :returns escaped query
    """
    patt = r'({}):([^:"\s]+|"[^"]+")\s*'.format('|'.join(placeholders.keys()))
    # Extract all placeholders
    p = [f'+{placeholders[x.group(1)]}:{x.group(2)}'
         for x in re.finditer(patt, query) if x.group(1) in placeholders]
    # Escape keyword based arguments
    query = escape(re.sub(patt, '', query)).strip()
    if query:
        p.append(f'+({query})')
    return ' '.join(p)


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
