# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import requests
from requests.exceptions import RequestException
from werkzeug.urls import url_join

from indico.modules.search.base import IndicoSearchProvider, SearchFilter

from indico_citadel import _
from indico_citadel.result_schemas import CitadelResultSchema
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

        operator = params.pop('default_operator', 'AND')
        filter_query, ranges = format_filters(params, filters, range_filters)
        # Look for objects matching the `query` and schema, make sure the query is properly escaped
        # https://cern-search.docs.cern.ch/usage/operations/#advanced-queries
        q = f'{format_query(query, {k: field for k, (field, _) in placeholders.items()})} {ranges}'
        search_params = {'page': page, 'size': self.RESULTS_PER_PAGE, 'q': q, 'highlight': '_data.*',
                         'type': [x.name for x in object_types], 'default_operator': operator, **filter_query}
        # Filter by the objects that can be viewed by users/groups in the `access` argument
        if access:
            search_params['access'] = ','.join(access)

        try:
            resp = requests.get(self.records_url, params=search_params, headers=headers)
            resp.raise_for_status()
        except RequestException:
            raise Exception('Failed contacting the search service')

        data = resp.json()
        return CitadelResultSchema(context={'results_per_page': self.RESULTS_PER_PAGE}).load(data)

    def get_placeholders(self):
        return [SearchFilter(key, label) for key, (_, label) in placeholders.items()]

    def get_filters(self):
        return [SearchFilter(key, label) for key, label in filters.items()]


placeholders = {
    'title': ('_data.title', _('The title an event, contribution, etc.)')),
    'person': ('_data.persons.name', _("A speaker, author or event chair's name")),
    'affiliation': ('_data.persons.affiliation', _("A speaker, author or event chair's affiliation")),
    'type': ('type', _('An entry type (such as conference, meeting, file, etc.)')),
    'venue': ('_data.location.venue_name', _("Name of the venue")),
    'room': ('_data.location.room_name', _("Name of the room")),
    'address': ('_data.location.address', _("Address of the venue")),
    'file': ('_data.filename', _("Name of the attached file")),
    'keyword': ('_data.keywords', _('A keyword associated with an event')),
    'category': ('category_path.title', _('The category of an event')),
}

range_filters = {
    'start_range': 'start_dt'
}

filters = {
    'affiliation': _('Affiliation'),
    'person': _('Person'),
    'type_format': _('Type'),
    'venue': _('Location'),
    'start_range': _('Date'),
    'category': _('Category'),
    'category_id': _('Category ID'),
}
