# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import os
import re
from datetime import datetime, timedelta
from xml.dom import minidom

import requests
from flask import jsonify, redirect, request
from flask_pluginengine import current_plugin
from lxml import etree
from werkzeug.urls import url_encode

from indico.core.db import db
from indico.core.plugins import get_plugin_template_module

from indico_search import SearchEngine
from indico_search_invenio.entries import Author, ContributionEntry, EventEntry, SubContributionEntry


class InvenioRemoteSearch(object):
    # In general it would be nice if some of the functionality here was provided by a base class, but
    # since most likely not all search backends distinguish between event/contribution collections,
    # the base class would have to be very generic.
    # But if someone ever integrates another search engine and uses this as a base, he is very welcome
    # to extract parts from here and move them into the indico_search plugins instead of copying it to
    # his own plugin!

    def __init__(self, engine):
        self.engine = engine

    @property
    def results_per_page(self):
        return current_plugin.settings.get('results_per_page')

    def process(self):
        if request.is_xhr:
            # AJAX request loading additional results
            return self.process_xhr()

        collections = set()
        if self.engine.values['collection'] in {'', 'events'}:
            collections.add('events')
        if self.engine.values['collection'] in {'', 'contributions'}:
            collections.add('contributions')

        result_data = {'query': {k: v for k, v in request.form.iterlists() if k != 'search-collection'},
                       'events': None,
                       'contributions': None}
        for collection in collections:
            result_data[collection] = self._query_results(collection, 1)

        if request.is_xhr:
            return jsonify(events=self._make_json_response(result_data['events'], True),
                           contributions=self._make_json_response(result_data['contributions']))

        return result_data

    def process_xhr(self):
        offset = int(request.form['offset'])
        collection = self.engine.values['collection']
        assert collection in {'events', 'contributions'}
        return jsonify(self._make_json_response(self._query_results(collection, offset), collection == 'events'))

    def _make_json_response(self, data, is_event):
        mod = get_plugin_template_module('_results.html')
        return {'html': '\n'.join(mod.render_result(r, is_event) for r in data['results']),
                'has_more': data['has_more'],
                'offset': data['offset']}

    def _query_results(self, collection, offset):
        num = self.results_per_page
        if self.engine.user:
            # Querying private data so we might have to skip some results - fetching more may avoid an extra query
            num *= 2
        params = self.engine.make_query(collection)
        results = []
        has_more = True
        while len(results) < self.results_per_page:
            data = self._process_data(self._fetch_data(of='xm', rg=num, jrec=offset, **params))
            if not data:
                # No results returned => stop searching, and we know for sure increasing the offset won't return more
                has_more = False
                break
            offset += len(data)
            for r in data:
                if not r.is_visible(self.engine.user):
                    continue
                results.append(r)
            # We might have more data than we want to show - remove those and also make sure they are found again in
            # the next batch of items
            extra = len(results) - self.results_per_page
            if extra > 0:
                del results[-extra:]
                offset -= extra
                break
            if len(data) < num:
                has_more = False
                break
        if not results:
            return None
        return {'has_more': has_more, 'offset': offset, 'results': results}

    def _fetch_data(self, **params):
        return requests.get(current_plugin.settings.get('search_url'), params=params).content

    def _process_data(self, data):
        xsl = etree.XSLT(etree.parse(os.path.join(current_plugin.root_path, 'marc2short.xsl')))
        xml = unicode(xsl(etree.fromstring(data)))
        doc = minidom.parseString(xml)
        return [self._process_record(e) for e in doc.getElementsByTagName('record')
                if e.getElementsByTagName('identifier')]

    def _process_record(self, elem):
        authors = []
        materials = []
        element_id = elem.getElementsByTagName('identifier')[0].firstChild.data

        try:
            title = elem.getElementsByTagName('title')[0].firstChild.data
        except (IndexError, AttributeError):
            title = None

        try:
            location = elem.getElementsByTagName('location')[0].firstChild.data
        except (IndexError, AttributeError):
            location = None

        try:
            start_date = elem.getElementsByTagName('start_date')[0].firstChild.data
            start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
        except (IndexError, AttributeError):
            start_date = None

        try:
            description = elem.getElementsByTagName('description')[0].firstChild.data
        except (IndexError, AttributeError):
            description = None

        for author in elem.getElementsByTagName('author'):
            name = author.getElementsByTagName('name')[0].firstChild.data
            try:
                role = author.getElementsByTagName('role')[0].firstChild.data
            except (IndexError, AttributeError):
                role = None

            try:
                affiliation = author.getElementsByTagName('affiliation')[0].firstChild.data
            except (IndexError, AttributeError):
                affiliation = None
            authors.append(Author(name, role, affiliation))

        for material in elem.getElementsByTagName('material'):
            try:
                material_url = material.getElementsByTagName('url')[0].firstChild.data
            except (IndexError, AttributeError):
                material_url = None

            try:
                material_description = material.getElementsByTagName('description')[0].firstChild.data
            except (IndexError, AttributeError):
                material_description = None
            materials.append((material_url, material_description))

        return self._make_result(element_id, title, location, start_date, materials, authors, description)

    def _make_result(self, entry_id, title, location, start_date, materials, authors, description):
        match = re.match(r'^INDICO\.(\w+)(\.(\w+)(\.(\w)+)?)?$', entry_id)
        if not match:
            raise Exception('unrecognized entry id: {}'.format(entry_id))

        if match.group(4):
            return SubContributionEntry(match.group(5), title, location, start_date, materials, authors, description,
                                        match.group(3), match.group(1))
        elif match.group(2):
            return ContributionEntry(match.group(3), title, location, start_date, materials, authors, description,
                                     match.group(1))
        else:
            return EventEntry(match.group(1), title, location, start_date, materials, authors, description)


class InvenioSearchEngine(SearchEngine):
    @property
    def use_redirect(self):
        return current_plugin.settings.get('display_mode') == 'redirect'

    @property
    def only_public(self):
        return current_plugin.settings.get('display_mode') != 'api_private'

    def process(self):
        query = self.make_query()
        if not any(query.viewvalues()):
            return None
        elif self.use_redirect:
            return redirect(self._build_url(**query))
        else:
            rs = InvenioRemoteSearch(self)
            return rs.process()

    def _build_url(self, **query_params):
        return '{}?{}'.format(current_plugin.settings.get('search_url'), url_encode(query_params))

    def make_query(self, collection=None):
        query = {}
        search_items = []
        # Main search term
        field = self.values['field']
        phrase = self.values['phrase']
        if phrase:
            if field == 'author':
                query['f'] = ''
                search_items += self._make_field_query(phrase, field)
            else:
                query['f'] = field
                search_items.append(phrase)
        # Collection
        if self.only_public:
            search_items.append(self._make_public_collection_query(collection))
        else:
            query['c'] = self._make_private_collection_query(collection)
        # Category/Event
        search_items.append(self._make_obj_query())
        # Date
        search_items.append(self._make_date_query())
        # Build query
        query['p'] = ' '.join(filter(None, search_items))
        # Sorting
        query['sf'] = 'date'
        query['so'] = self.values['sort_order']
        return query

    def _make_field_query(self, phrase, field):
        if phrase[0] == '"' and phrase[-1] == '"':
            return ['{}:"{}"'.format(field, phrase.replace('"', ''))]
        return ['{}:{}'.format(field, word) for word in phrase.split()]

    def _make_date_query(self):
        start_date = self.values['start_date']
        end_date = self.values['end_date']
        if not start_date and not end_date:
            return None
        start_date = start_date.strftime('%Y-%m-%d') if start_date else '1950'
        end_date = (end_date + timedelta(days=1)).strftime('%Y-%m-%d') if end_date else '2100'
        return '518__d:"{}"->"{}"'.format(start_date, end_date)

    def _make_public_collection_query(self, collection=None):
        if collection is None:
            collection = self.values['collection']
        if collection == 'events':
            return """970__a:"INDICO.*" -970__a:'.*.'"""
        elif collection == 'contributions':
            return """970__a:"INDICO.*" 970__a:'.*.'"""
        else:
            # XXX: This was missing in the old plugin, but I think it's necessary to get only Indico results
            return '970__a:"INDICO.*"'

    def _make_private_collection_query(self, collection=None):
        if collection is None:
            collection = self.values['collection']
        suffix = 'CONTRIBS' if collection == 'contributions' else 'EVENTS'
        prefix = 'INDICOSEARCH' if self.user else 'INDICOSEARCH.PUBLIC'
        return '{}.{}'.format(prefix, suffix)

    def _make_obj_query(self):
        if isinstance(self.obj, db.m.Category) and not self.obj.is_root:
            return '650_7:"{}*"'.format(':'.join(unicode(c['id']) for c in self.obj.chain))
        elif isinstance(self.obj, db.m.Event):
            # XXX: The old plugin prefixed this with 'AND ' but according to the invenio docs, AND is implied
            return '970__a:"INDICO.{}.*"'.format(self.obj.id)
