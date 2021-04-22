# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import asyncio
import re
from concurrent.futures.thread import ThreadPoolExecutor
from functools import wraps

from flask import current_app


def parallelize(func, entries, batch_size=200):
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=batch_size)
        tasks = []
        for entry in entries:
            def run(app, *_args, **_kwargs):
                with app.app_context():
                    return func(*_args, **_kwargs)
            tasks.append(loop.run_in_executor(
                executor, run, current_app._get_current_object(), entry, *args, **kwargs
            ))
            if len(tasks) >= batch_size:
                loop.run_until_complete(asyncio.gather(*tasks))
                del tasks[:]
        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks))

    return wrapper


def format_query(query, placeholders):
    """Format and split the query into keywords and placeholders.

    https://cern-search.docs.cern.ch/usage/operations/#advanced-queries

    :param query: search query
    :param placeholders: placeholder whitelist
    :returns escaped query
    """
    patt = r'({}):([^:"\s]+|".+")\s*'.format('|'.join(placeholders.keys()))
    # Extract all placeholders
    p = ['+{}:{}'.format(placeholders[x.group(1)], x.group(2))
         for x in re.finditer(patt, query) if x.group(1) in placeholders]
    # Escape keyword based arguments
    query = escape(re.sub(patt, '', query))
    return '{} {}'.format(' '.join(p), query).strip()


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
                query.append('+{}:{}'.format(range_filters[k], v))
            continue
        _filters[k] = v
    return _filters, ' '.join(query)


def escape(query):
    """Prepend all special ElasticSearch characters with a backslash."""
    patt = r'([+\-=><!(){}[\]\^"~*?:\\\/]|&&|\|\|)'
    return re.sub(patt, r'\\\1', query)
