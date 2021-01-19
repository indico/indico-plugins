# This file is part of the CERN Indico plugins.
# Copyright (C) 2014 - 2021 CERN
#
# The CERN Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License; see
# the LICENSE file for more details.

from math import ceil

from marshmallow import INCLUDE
from indico.core.plugins import IndicoPlugin
from indico.core import signals
from data import CONTRIB_DATA, FILE_DATA
from indico.modules.search.schemas import ContributionSchema, AttachmentSchema, BaseSchema
from indico.modules.search.base import IndicoSearchProvider, SearchTarget


class DummySearchPlugin(IndicoPlugin):
    def init(self):
        super(DummySearchPlugin, self).init()
        self.connect(signals.get_search_providers, self.get_search_providers)

    def get_search_providers(self, sender, **kwargs):
        yield TestSearch


class TestSearch(IndicoSearchProvider):
    DATA = {
        SearchTarget.contribution: (ContributionSchema, CONTRIB_DATA),
        SearchTarget.attachment: (AttachmentSchema, FILE_DATA)
    }

    @classmethod
    def search(cls, query, access, object_type=SearchTarget.event, page=1):
        schema, store = cls.DATA[object_type] if object_type in cls.DATA else (BaseSchema, [])
        data = [x for x in store if query.lower() in x['title'].lower()]
        total = len(data)
        pages = int(ceil(total / cls.RESULTS_PER_PAGE))
        offset = (page - 1) * cls.RESULTS_PER_PAGE
        items = data[offset:offset + cls.RESULTS_PER_PAGE]
        results = schema(many=True).dump(items)
        return {'results': results, 'page': page, 'pages': pages, 'total': total }
