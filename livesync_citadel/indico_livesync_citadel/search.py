# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re

import requests
from werkzeug.urls import url_join

from indico.modules.search.base import IndicoSearchProvider, SearchTarget


class CitadelProvider(IndicoSearchProvider):
    def __init__(self, *args, **kwargs):
        from indico_livesync_citadel.plugin import LiveSyncCitadelPlugin

        super().__init__(*args, **kwargs)
        self.token = LiveSyncCitadelPlugin.settings.get('search_backend_token')
        self.backend_url = LiveSyncCitadelPlugin.settings.get('search_backend_url')
        self.records_url = url_join(self.backend_url, 'api/records/')

    def search(self, query, access, object_type=SearchTarget.event, page=1, params=None, highlight=True):
        # https://cern-search.docs.cern.ch/usage/operations/#query-documents
        # this token is used by the backend to authenticate and also to filter
        # the objects that we can actually read
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }

        # look for objects matching the `query` and schema, make sure the query is properly escaped
        # https://cern-search.docs.cern.ch/usage/operations/#advanced-queries
        q = '{} +type:{}'.format(format_query(query), object_type.name)
        _filters = {k: params[k] for k, v in filters.items() if k in params}
        params = {'page': page, 'size': self.RESULTS_PER_PAGE, 'q': q, 'highlight': '_data.*', **_filters}
        # filter by the objects that can be viewed by users/groups in the `access` argument
        if access:
            params['access'] = ','.join(access)

        resp = requests.get(self.records_url, params=params, headers=headers, verify=False)
        if not resp.ok:
            return 0, [], []

        resp = resp.json()
        _aggregations, hits = resp['aggregations'], resp['hits']
        total, _objects = hits['total'], hits['hits']

        aggregations = [
            {
                'key': key,
                'label': filters[key],
                'buckets': value['buckets']
            }
            for key, value in _aggregations.items()
            if len(key) and key in filters
        ]
        # The citadel service stores every indexable/queryable attribute in a _data
        # This extraction should ensure Indico is abstracted from that complexity
        objects = [
            {
                **o['metadata'].pop('_data'),
                **o['metadata'],
                'highlight': {
                    re.sub(r'^_data\.', '', key): value for key, value in o['highlight'].items()
                }
            }
            for o in _objects
        ]
        return total, objects, aggregations


placeholders = {
    'title': '_data.title',
    'person': '_data.persons.name',
    'affiliation': '_data.persons.affiliation',
    'type': '_data.type',
    'venue': '_data.location.venue_name',  # TODO: multiple locations,
    'keyword': '_data.keywords'
}

# TODO: potentially move this to Indico:
# - restrict the filters we support
# - provide i18n to them
filters = {
    'affiliation': 'Affiliation',
    'person': 'Person',
    'type_format': 'Type',
    'venue': 'Location',
    'start_range': 'Start Date',
    'created_range': 'Created Date',
    'modified_range': 'Modified Date'
}


def format_query(query):
    patt = r'({}):([^:"\s]+|".+")\s*'.format('|'.join(placeholders.keys()))
    p = ['+{}:{}'.format(placeholders[x.group(1)], x.group(2))
         for x in re.finditer(patt, query) if x.group(1) in placeholders]
    query = escape(re.sub(patt, '', query))
    return '{} +{}'.format(' '.join(p), query).strip()


def escape(query):
    """Prepend all special ElasticSearch characters with a slash"""
    patt = r'([\+\-\=\>\<!\(\)\{\}\[\]\^"~\*\?:\\/]|&&|\|\|)'
    return re.sub(patt, r'\\\1', query)
