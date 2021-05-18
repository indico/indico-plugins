# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest

from indico_citadel.util import _flatten, format_aggregations, format_query, remove_none_entries


@pytest.mark.parametrize(('query', 'expected'), [
    ('title:"my event" ola person:john ola some:yes ola',
     'title:"my event" ola person:john ola some\\:yes ola'),
    ('title:"my title:something"', 'title:"my title\\:something"'),
    ('hello   ', 'hello'),
    ('hey title:something', 'hey title:something'),
    ('title:something hey', 'title:something hey'),
    ('hey title:something hey person:john', 'hey title:something hey person:john'),
    ('<*\\^()', '\\<*\\\\\\^\\(\\)'),
    ('file:*.pdf', 'file:*.pdf'),
    ('title:"meeting" "jane doe"', 'title:"meeting" "jane doe"'),
    ('"section meeting" OR "group meeting"', '"section meeting" OR "group meeting"'),
    ('title:meeting AND "indico"', 'title:meeting AND "indico"'),
    ('title:valid stringtitle:valid foo:bar', 'title:valid stringtitle\\:valid foo\\:bar')
])
def test_query_placeholders(query, expected):
    placeholders = {'title': 'title', 'person': 'person', 'file': 'file'}
    assert format_query(query, placeholders) == expected


@pytest.mark.parametrize(('val', 'expected'), [
    ({'a': 0, 'b': None, 'c': {'c1': None, 'c2': 0, 'c3': {'c3a': None}}},
     {'a': 0, 'c': {'c2': 0, 'c3': {}}}),
    ({'a': 0, 'b': [None, {'b1': None, 'b2': 'test'}]},
     {'a': 0, 'b': [None, {'b2': 'test'}]}),
    (None, None),
])
def test_remove_none_entries(val, expected):
    assert remove_none_entries(val) == expected


@pytest.mark.parametrize(('val', 'expected'), [
    ({'person': {'name': {'buckets': []}, 'affiliation': {'buckets': []}}, 'other': {'other': {'buckets': []}}},
     {'person_name', 'person_affiliation', 'other_other'}),
    ({'other': {'other': {'other': {'other': {'buckets': []}}}}},
     {'other_other_other_other'})
])
def test_flatten(val, expected):
    assert {key for key, _ in _flatten(val)} == expected


def test_format_aggregations():
    aggs = {
        'author': {
            'buckets': [
                {'doc_count': 120, 'key': 'Mike Eatsalot'},
                {'doc_count': 117, 'key': 'Dr Banner Bruce'},
            ],
            'doc_count_error_upper_bound': 22,
            'sum_other_doc_count': 6766,
        },
        'category': {
            'buckets': [
                {'doc_count': 4484, 'key': 'Home'},
                {'doc_count': 1210, 'key': 'Departments'},
                {'doc_count': 1158, 'key': 'Schools, Seminars and Courses'},
                {'doc_count': 885, 'key': 'Projects'},
            ],
            'doc_count_error_upper_bound': 142,
            'sum_other_doc_count': 10702,
        },
        'keyword': {
            'buckets': [
                {'doc_count': 175, 'key': 'lhc'},
                {'doc_count': 16, 'key': 'lhc circuits'},
                {'doc_count': 16, 'key': 'modeling'},
            ],
            'doc_count_error_upper_bound': 7,
            'sum_other_doc_count': 747,
        },
        'person': {
            'affiliation': {
                'buckets': [
                    {
                        'doc_count': 2452,
                        'key': 'cern',
                        'most_common': {
                            'buckets': [{'doc_count': 2451, 'key': 'CERN'}],
                            'doc_count_error_upper_bound': 0,
                            'sum_other_doc_count': 1,
                        },
                    },
                    {
                        'doc_count': 79,
                        'key': 'fermi national accelerator lab. (us)',
                        'most_common': {
                            'buckets': [
                                {
                                    'doc_count': 79,
                                    'key': 'Fermi National Accelerator Lab. (US)',
                                }
                            ],
                            'doc_count_error_upper_bound': 0,
                            'sum_other_doc_count': 0,
                        },
                    },
                ],
                'doc_count_error_upper_bound': 18,
                'sum_other_doc_count': 3399,
            },
            'doc_count': 7527,
            'name': {
                'buckets': [
                    {
                        'doc_count': 120,
                        'key': 'mike eatsalot',
                        'most_common': {
                            'buckets': [
                                {'doc_count': 120, 'key': 'Mike Eatsalot'}
                            ],
                            'doc_count_error_upper_bound': 0,
                            'sum_other_doc_count': 0,
                        },
                    },
                    {
                        'doc_count': 117,
                        'key': 'dr banner bruce',
                        'most_common': {
                            'buckets': [{'doc_count': 117, 'key': 'Dr Banner Bruce'}],
                            'doc_count_error_upper_bound': 0,
                            'sum_other_doc_count': 0,
                        },
                    },
                ],
                'doc_count_error_upper_bound': 22,
                'sum_other_doc_count': 6779,
            },
        },
        'start_range': {
            'buckets': [
                {
                    'doc_count': 3974,
                    'key': 'More than a year ago',
                    'to': 1577836800000.0,
                    'to_as_string': '2020-01-01',
                },
                {
                    'doc_count': 431,
                    'from': 1577836800000.0,
                    'from_as_string': '2020-01-01',
                    'key': 'Up to a year',
                    'to': 1617235200000.0,
                    'to_as_string': '2021-04-01',
                },
                {
                    'doc_count': 39,
                    'from': 1617235200000.0,
                    'from_as_string': '2021-04-01',
                    'key': 'Up to a month',
                    'to': 1620604800000.0,
                    'to_as_string': '2021-05-10',
                },
                {
                    'doc_count': 40,
                    'from': 1620604800000.0,
                    'from_as_string': '2021-05-10',
                    'key': 'Up to a week',
                },
                {
                    'doc_count': 35,
                    'from': 1621296000000.0,
                    'from_as_string': '2021-05-18',
                    'key': 'Today',
                },
            ]
        },
        'type_format': {
            'buckets': [
                {'doc_count': 2113, 'key': 'lecture'},
                {'doc_count': 1528, 'key': 'meeting'},
                {'doc_count': 843, 'key': 'conference'},
            ],
            'doc_count_error_upper_bound': 0,
            'sum_other_doc_count': 0,
        },
        'venue': {
            'buckets': [
                {
                    'doc_count': 3197,
                    'key': 'cern',
                    'most_common': {
                        'buckets': [{'doc_count': 3197, 'key': 'CERN'}],
                        'doc_count_error_upper_bound': 0,
                        'sum_other_doc_count': 0,
                    },
                },
                {
                    'doc_count': 397,
                    'key': '',
                    'most_common': {
                        'buckets': [{'doc_count': 397, 'key': ''}],
                        'doc_count_error_upper_bound': 0,
                        'sum_other_doc_count': 0,
                    },
                },
                {
                    'doc_count': 63,
                    'key': 'other institutes',
                    'most_common': {
                        'buckets': [{'doc_count': 63, 'key': 'Other Institutes'}],
                        'doc_count_error_upper_bound': 0,
                        'sum_other_doc_count': 0,
                    },
                },
            ],
            'doc_count_error_upper_bound': 4,
            'sum_other_doc_count': 653,
        },
    }

    filters = {
        'person_affiliation': 'Affiliation',
        'person_name': 'Person',
        'type_format': 'Type',
        'venue': 'Location',
        'start_range': 'Date',
        'category': 'Category',
        'category_id': 'Category ID',
        'event_id': 'Event ID',
    }

    expected = {
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

    assert format_aggregations(aggs, filters) == expected
