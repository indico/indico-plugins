# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest

from indico_citadel.util import format_query, remove_none_entries


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
