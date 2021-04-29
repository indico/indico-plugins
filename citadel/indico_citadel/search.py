# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import math

import requests
from requests.exceptions import RequestException
from werkzeug.urls import url_join

from indico.modules.search.base import IndicoSearchProvider

from indico_citadel import _
from indico_citadel.util import format_filters, format_query


class CitadelProvider(IndicoSearchProvider):
    def __init__(self, *args, **kwargs):
        from indico_citadel.plugin import CitadelPlugin

        super().__init__(*args, **kwargs)
        self.token = CitadelPlugin.settings.get('search_backend_token')
        self.backend_url = CitadelPlugin.settings.get('search_backend_url')
        self.records_url = url_join(self.backend_url, 'api/records/')

    def search(self, query, access, page=1, object_types=(), **params):
        # https://cern-search.docs.cern.ch/usage/operations/#query-documents
        # this token is used by the backend to authenticate and also to filter
        # the objects that we can actually read
        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        filter_query, ranges = format_filters(params, filters, range_filters)
        # Look for objects matching the `query` and schema, make sure the query is properly escaped
        # https://cern-search.docs.cern.ch/usage/operations/#advanced-queries
        q = f'{format_query(query, {k: field for k, (field, _) in placeholders.items()})} {ranges}'
        search_params = {'page': page, 'size': self.RESULTS_PER_PAGE, 'q': q, 'highlight': '_data.*',
                         'type': [x.name for x in object_types], **filter_query}
        # Filter by the objects that can be viewed by users/groups in the `access` argument
        if access:
            search_params['access'] = ','.join(access)

        try:
            resp = requests.get(self.records_url, params=search_params, headers=headers)
            resp.raise_for_status()
        except RequestException:
            raise Exception('Failed contacting the search service')

        resp = resp.json()
        _aggregations, hits = resp['aggregations'], resp['hits']
        total, _objects = hits['total'], hits['hits']

        aggregations = {
            key: {
                'label': filters[key],
                'buckets': value['buckets']
            }
            for key, value in _aggregations.items()
            if key in filters
        }
        # The citadel service stores every indexable/queryable attribute in a _data
        # This extraction should ensure Indico is abstracted from that complexity
        objects = [
            {
                **o['metadata'].pop('_data'),
                **o['metadata'],
                'highlight': {
                    key.removeprefix('_data.'): value for key, value in o['highlight'].items()
                }
            }
            for o in _objects
        ]
        return total, min(math.ceil(total / self.RESULTS_PER_PAGE), 1000), objects, aggregations

    def get_placeholders(self):
        return [{'key': key, 'label': label} for key, (_, label) in placeholders.items()]


placeholders = {
    'title': ('_data.title', _('An entry title (such as: event, contribution, attachment, event_note)')),
    'person': ('_data.persons.name', _("A speaker, author or event chair's name")),
    'affiliation': ('_data.persons.affiliation', _("A speaker, author or event chair's affiliation")),
    'type': ('_data.type', _('An entry type (such as: conference, meeting, link, file)')),
    'venue': ('_data.location.venue_name', _("The event's venue name")),  # TODO: multiple locations
    'keyword': ('_data.keywords', _('A keyword associated with an event'))
}

range_filters = {
    'start_range': 'start_dt'
}

# TODO: potentially move this to Indico (and provide i18n)
filters = {
    'affiliation': 'Affiliation',
    'person': 'Person',
    'type_format': 'Type',
    'venue': 'Location',
    'start_range': 'Start Date',
}
