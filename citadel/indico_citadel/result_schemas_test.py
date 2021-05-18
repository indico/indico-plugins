# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from marshmallow import fields

from indico.core.marshmallow import mm

from indico_citadel.result_schemas import CitadelAggregationSchema


def test_aggregations():
    class TestSchema(mm.Schema):
        aggregations = fields.Dict(fields.String(), fields.Nested(CitadelAggregationSchema))

    aggregations = {
        'category': {
            'label': 'Category',
            'buckets': [
                {'key': 'Home', 'count': 4484},
                {'key': 'Departments', 'count': 1210},
                {'key': 'Schools, Seminars and Courses', 'count': 1158},
                {'key': 'Projects', 'count': 885},
            ]
        },
        'person_affiliation': {
            'label': 'Affiliation',
            'buckets': [
                {'key': 'CERN', 'count': 2452},
                {'key': 'Fermi National Accelerator Lab. (US)', 'count': 79},
            ],
        },
        'person_name': {
            'label': 'Person',
            'buckets': [
                {'key': 'Mike Eatsalot', 'count': 120},
                {'key': 'Dr Banner Bruce', 'count': 117},
            ],
        },
        'start_range': {
            'label': 'Date',
            'buckets': [
                {
                    'key': 'More than a year ago',
                    'count': 3974,
                    'to_as_string': '2020-01-01',
                },
                {
                    'key': 'Up to a year',
                    'count': 431,
                    'from_as_string': '2020-01-01',
                    'to_as_string': '2021-04-01',
                },
                {
                    'key': 'Up to a month',
                    'count': 39,
                    'from_as_string': '2021-04-01',
                    'to_as_string': '2021-05-10',
                },
                {'key': 'Up to a week', 'count': 40, 'from_as_string': '2021-05-10'},
                {'key': 'Today', 'count': 35, 'from_as_string': '2021-05-18'},
            ],
        },
        'type_format': {
            'label': 'Type',
            'buckets': [
                {'key': 'lecture', 'count': 2113},
                {'key': 'meeting', 'count': 1528},
                {'key': 'conference', 'count': 843},
            ],
        },
        'venue': {
            'label': 'Location',
            'buckets': [
                {'key': 'CERN', 'count': 3197},
                {'key': '', 'count': 397},
                {'key': 'Other Institutes', 'count': 63},
            ],
        },
    }

    expected = {
        'aggregations': {
            'category': {
                'buckets': [
                    {'count': 4484, 'filter': 'Home', 'key': 'Home'},
                    {'count': 1210, 'filter': 'Departments', 'key': 'Departments'},
                    {
                        'count': 1158,
                        'filter': 'Schools, Seminars and Courses',
                        'key': 'Schools, Seminars and Courses',
                    },
                    {'count': 885, 'filter': 'Projects', 'key': 'Projects'},
                ],
                'label': 'Category',
            },
            'person_affiliation': {
                'buckets': [
                    {'count': 2452, 'filter': 'CERN', 'key': 'CERN'},
                    {
                        'count': 79,
                        'filter': 'Fermi National Accelerator Lab. (US)',
                        'key': 'Fermi National Accelerator Lab. (US)',
                    },
                ],
                'label': 'Affiliation',
            },
            'person_name': {
                'buckets': [
                    {'count': 120, 'filter': 'Mike Eatsalot', 'key': 'Mike Eatsalot'},
                    {
                        'count': 117,
                        'filter': 'Dr Banner Bruce',
                        'key': 'Dr Banner Bruce',
                    },
                ],
                'label': 'Person',
            },
            'start_range': {
                'buckets': [
                    {
                        'count': 3974,
                        'filter': '[* TO 2020-01-01]',
                        'key': 'More than a year ago',
                    },
                    {
                        'count': 431,
                        'filter': '[2020-01-01 TO 2021-04-01]',
                        'key': 'Up to a year',
                    },
                    {
                        'count': 39,
                        'filter': '[2021-04-01 TO 2021-05-10]',
                        'key': 'Up to a month',
                    },
                    {'count': 40, 'filter': '[2021-05-10 TO *]', 'key': 'Up to a week'},
                    {'count': 35, 'filter': '[2021-05-18 TO *]', 'key': 'Today'},
                ],
                'label': 'Date',
            },
            'type_format': {
                'buckets': [
                    {'count': 2113, 'filter': 'lecture', 'key': 'lecture'},
                    {'count': 1528, 'filter': 'meeting', 'key': 'meeting'},
                    {'count': 843, 'filter': 'conference', 'key': 'conference'},
                ],
                'label': 'Type',
            },
            'venue': {
                'buckets': [
                    {'count': 3197, 'filter': 'CERN', 'key': 'CERN'},
                    {'count': 397, 'filter': '', 'key': ''},
                    {
                        'count': 63,
                        'filter': 'Other Institutes',
                        'key': 'Other Institutes',
                    },
                ],
                'label': 'Location',
            },
        },
    }

    assert TestSchema().load({'aggregations': aggregations}) == expected
