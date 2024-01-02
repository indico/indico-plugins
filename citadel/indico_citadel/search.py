# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import base64
import zlib
from urllib.parse import urljoin

import requests
from flask import current_app
from requests.exceptions import RequestException

from indico.modules.search.base import IndicoSearchProvider, SearchOption
from indico.util.decorators import classproperty

from indico_citadel import _
from indico_citadel.result_schemas import CitadelResultSchema
from indico_citadel.util import format_filters, format_query, get_user_access


class CitadelProvider(IndicoSearchProvider):
    def __init__(self, *args, **kwargs):
        from indico_citadel.plugin import CitadelPlugin

        super().__init__(*args, **kwargs)
        self.token = CitadelPlugin.settings.get('search_backend_token')
        self.backend_url = CitadelPlugin.settings.get('search_backend_url')
        self.records_url = urljoin(self.backend_url, 'api/records/')

    @classproperty
    @classmethod
    def active(cls):
        from indico_citadel.plugin import CitadelPlugin
        if current_app.config['TESTING']:
            return True
        elif CitadelPlugin.settings.get('disable_search'):
            return False
        return bool(CitadelPlugin.settings.get('search_backend_url') and
                    CitadelPlugin.settings.get('search_backend_token'))

    def search(self, query, user=None, page=1, object_types=(), *, admin_override_enabled=False,
               **params):
        # https://cern-search.docs.cern.ch/usage/operations/#query-documents
        # this token is used by the backend to authenticate and also to filter
        # the objects that we can actually read
        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        operator = params.pop('default_operator', 'AND')
        sort = params.pop('sort', None)
        filter_query, ranges = format_filters(params, filters, range_filters)
        # Look for objects matching the `query` and schema, make sure the query is properly escaped
        # https://cern-search.docs.cern.ch/usage/operations/#advanced-queries
        parts = [format_query(query, {k: field for k, (field, _) in placeholders.items()})]
        if ranges:
            parts.append(ranges)
        search_params = {
            'page': page, 'size': self.RESULTS_PER_PAGE, 'q': ' '.join(parts), 'highlight': '_data.*',
            'type': [x.name for x in object_types], 'sort': sort, 'default_operator': operator,
            **filter_query
        }
        # Filter by the objects that can be viewed by users/groups in the `access` argument
        if access := get_user_access(user, admin_override_enabled):
            access_string = ','.join(access)
            if len(access_string) > 1024:
                access_string_gz = base64.b64encode(zlib.compress(access_string.encode(), level=9))
                search_params['access_gz'] = access_string_gz
            else:
                search_params['access'] = access_string

        try:
            resp = requests.get(self.records_url, params=search_params, headers=headers)
            resp.raise_for_status()
        except RequestException:
            raise Exception('Failed contacting the search service')

        data = resp.json()
        return CitadelResultSchema(context={'results_per_page': self.RESULTS_PER_PAGE}).load(data)

    def get_placeholders(self):
        return [SearchOption(key, label) for key, (_, label) in placeholders.items()]

    def get_sort_options(self):
        return [SearchOption(key, label) for key, label in sort_options.items()]


placeholders = {
    'title': ('_data.title', _('The title of an event, contribution, etc.')),
    'person': ('_data.persons_index.name', _("A speaker, author or event chair's name")),
    'affiliation': ('_data.persons_index.affiliation', _("A speaker, author or event chair's affiliation")),
    'type': ('type_any', _('An entry type (such as conference, meeting, file, etc.)')),
    'venue': ('_data.location.venue_name', _('Name of the venue')),
    'room': ('_data.location.room_name', _('Name of the room')),
    'address': ('_data.location.address', _('Address of the venue')),
    'file': ('_data.filename', _('Name of the attached file')),
    'keyword': ('_data.keywords', _('A keyword associated with an event')),
    'category': ('category_path.title', _('The category of an event')),
}

range_filters = {
    'start_range': 'start_dt'
}

sort_options = {
    'bestmatch': _('Most relevant'),
    'mostrecent': _('Newest first'),
    '-mostrecent': _('Oldest first')
}

filters = {
    'person_affiliation': _('Affiliation'),
    'person_name': _('Person'),
    'type_format': _('Type'),
    'venue': _('Location'),
    'start_range': _('Date'),
    'category': _('Category'),
    'category_id': _('Category ID'),
    'event_id': _('Event ID'),
}
