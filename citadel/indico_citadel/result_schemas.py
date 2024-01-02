# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import math

from marshmallow import fields, pre_load

from indico.modules.search.base import SearchTarget
from indico.modules.search.result_schemas import (AggregationSchema, AttachmentResultSchema, BucketSchema,
                                                  EventNoteResultSchema, EventResultSchema, ResultItemSchema,
                                                  ResultSchema)

from indico_citadel.util import format_aggregations


class CitadelEventResultSchema(EventResultSchema):
    @pre_load
    def _translate_keys(self, data, **kwargs):
        data = data.copy()
        data['event_type'] = data.pop('type_format')
        return data


class CitadelAttachmentResultSchema(AttachmentResultSchema):
    @pre_load
    def _translate_keys(self, data, **kwargs):
        data = data.copy()
        data['user'] = data.pop('persons', None)
        data['attachment_type'] = data.pop('type_format')
        return data


class CitadelEventNoteResultSchema(EventNoteResultSchema):
    @pre_load
    def _translate_keys(self, data, **kwargs):
        data = data.copy()
        data['user'] = data.pop('persons', None)
        return data


class _CitadelBucketSchema(BucketSchema):
    @pre_load
    def _make_filter(self, data, **kwargs):
        data = data.copy()
        range_from = data.pop('from_as_string', None)
        range_to = data.pop('to_as_string', None)
        if range_from or range_to:
            data['filter'] = f'[{range_from or "*"} TO {range_to or "*"}]'
        else:
            data['filter'] = data['key']
        return data


class CitadelAggregationSchema(AggregationSchema):
    buckets = fields.List(fields.Nested(_CitadelBucketSchema))


class CitadelResultItemSchema(ResultItemSchema):
    type_schemas = {
        **ResultItemSchema.type_schemas,
        SearchTarget.event.name: CitadelEventResultSchema,
        SearchTarget.attachment.name: CitadelAttachmentResultSchema,
        SearchTarget.event_note.name: CitadelEventNoteResultSchema,
    }


class CitadelResultSchema(ResultSchema):
    results = fields.List(fields.Nested(CitadelResultItemSchema), required=True)
    aggregations = fields.Dict(fields.String(), fields.Nested(CitadelAggregationSchema))

    @pre_load
    def _extract_data(self, data, **kwargs):
        from .search import filters

        total = data['hits']['total']
        pages = min(1000, math.ceil(total / self.context['results_per_page']))
        # The citadel service stores every indexable/queryable attribute in a _data
        # This extraction should ensure Indico is abstracted from that complexity
        results = [
            {
                **item['metadata'].pop('_data'),
                **item['metadata'],
                'highlight': {
                    key.removeprefix('_data.'): value for key, value in item['highlight'].items()
                }
            }
            for item in data['hits']['hits']
        ]
        return {
            'aggregations': format_aggregations(data['aggregations'], filters),
            'results': results,
            'total': total,
            'pages': pages,
        }
