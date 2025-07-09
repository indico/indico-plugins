# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re
import sys
import threading
from collections import defaultdict
from functools import wraps

from flask import current_app
from flask.globals import _cv_app

from indico.core.db import db
from indico.core.db.sqlalchemy.principals import PrincipalMixin, PrincipalPermissionsMixin, PrincipalType
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
        main_app_context = _cv_app.get(None)
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
    :return: escaped query
    """
    placeholder_pat = re.compile(r'^(\w+):([^:"\s]+|"[^"]+")')
    keys = []

    while query:
        if m := placeholder_pat.match(query):
            p = m.group(1)
            if p in placeholders:
                keys.append(f'{placeholders[m.group(1)]}:{escape(m.group(2))}')
            else:
                keys.append(escape(m.group(0)))
            query = query[m.end():]
        else:
            # No match, consume one character and try again
            keys.append(escape(query[0]))
            query = query[1:]

    return ''.join(keys).strip()


def format_filters(params, filters, range_filters):
    """Extract any special placeholder filter, such as ranges, from the query params.

    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#_ranges

    :param params: The filter query params
    :param filters: The filter whitelist
    :param range_filters: The range filter whitelist
    :return: filters, extracted placeholders
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


def format_aggregations(aggregations, filters):
    """Format aggregations into a bucket dictionary.

    Besides transforming each aggregation, ensures each bucket key
    contains the most common result as defined from Elastic Search.

    :param aggregations: The raw aggregation object
    :param filters: The filter whitelist
    :return: key: {label, buckets: [{key, count}]}
    """
    return {
        key: {
            'label': str(filters[key]),
            'buckets': [{
                'key': bucket['most_common']['buckets'][0]['key'] if 'most_common' in bucket else bucket['key'],
                'count': bucket['doc_count'],
                **{k: v for k, v in bucket.items() if k in ('from_as_string', 'to_as_string')}
            } for bucket in value['buckets']]
        }
        for key, value in _flatten(aggregations)
        if key in filters
    }


def _flatten(obj, target_key='buckets', parent_key=''):
    if not isinstance(obj, dict):
        return
    if target_key in obj:
        yield parent_key, obj
    for key, value in obj.items():
        yield from _flatten(value, target_key, f'{parent_key}_{key}' if parent_key else key)


@memoize_redis(86400)
def _get_alternative_group_names():
    """Get non-lowercase versions of group names."""
    classes = [sc for sc in [*PrincipalMixin.__subclasses__(), *PrincipalPermissionsMixin.__subclasses__()]
               if hasattr(sc, 'query')]
    alternatives = defaultdict(set)
    for cls in classes:
        res = (db.session.query(cls.multipass_group_provider, cls.multipass_group_name)
               .distinct()
               .filter(cls.type == PrincipalType.multipass_group,
                       cls.multipass_group_name != db.func.lower(cls.multipass_group_name))
               .all())
        for provider, name in res:
            alternatives[(provider, name.lower())].add(name)
    return dict(alternatives)


def _include_capitalized_groups(groups):
    alternatives = _get_alternative_group_names()
    for group in groups:
        yield group.persistent_identifier
        for alt_name in alternatives.get((group.provider, group.name.lower()), ()):
            yield GroupProxy(alt_name, group.provider).persistent_identifier


@memoize_redis(3600)
def get_user_access(user, admin_override_enabled=False):
    if not user:
        return []
    if admin_override_enabled and user.is_admin:
        return ['IndicoAdmin']
    access = [user.persistent_identifier] + [u.persistent_identifier for u in user.get_merged_from_users_recursive()]
    access += [GroupProxy(x.id, _group=x).persistent_identifier for x in user.local_groups]
    if user.can_get_all_multipass_groups:
        multipass_groups = [GroupProxy(x.name, x.provider.name, x)
                            for x in user.iter_all_multipass_groups()]
        access += _include_capitalized_groups(multipass_groups)
    return access
