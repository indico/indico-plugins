# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import re

import requests
from werkzeug.urls import url_join

from indico_livesync_citadel.plugin import LiveSyncCitadelPlugin
from indico_livesync_citadel.models.search_id_map import EntryType


def escape(query):
    """Prepend all special ElasticSearch characters with a slash"""
    patt = r'([\+\-\=\>\<!\(\)\{\}\[\]\^"~\*\?:\\/]|&&|\|\|)'
    return re.sub(patt, r'\\\1', query)


# https://cern-search.docs.cern.ch/usage/operations/#query-documents
def search(query, access=None, object_type=EntryType.event, page=1):
    token = LiveSyncCitadelPlugin.settings.get('search_backend_token')
    search_backend_url = LiveSyncCitadelPlugin.settings.get('search_backend_url')
    query_url = url_join(search_backend_url, 'api/records/')

    # this token is used by the backend to authenticate and also to filter
    # the objects that we can actually read
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    # look for objects matching the `query` and schema
    # make sure the query is properly escaped (https://cern-search.docs.cern.ch/usage/operations/#advanced-queries)
    q = '+{} +$schema:*{}*'.format(escape(query), object_type.name)
    params = {'page': page, 'q': q}

    # filter by the objects that can be viewed by users/groups in the `access` argument
    if access:
        params['access'] = ','.join(access)

    resp = requests.get(query_url, params=params, headers=headers)
    if not resp.ok:
        return []

    resp = resp.json()
    aggregations, hits = resp['aggregations'], resp['hits']
    total, objects = hits['total'], hits['hits']
    return total, objects, aggregations
