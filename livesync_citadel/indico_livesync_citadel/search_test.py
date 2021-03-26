# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from unittest.mock import patch

import pytest

from indico_livesync_citadel.search import format_query


@patch('indico_livesync_citadel.search.placeholders', {
    'title': 'title',
    'person': 'person'
})
@pytest.mark.parametrize('query,expected', [
    ('title:"my event" ola person:john ola some:yes ola',
     '+title:"my event" +person:john ola ola some\\:yes ola'),
    ('title:"my title:something"', '+title:"my title:something"'),
    ('hello', 'hello'),
    ('hey title:something', '+title:something hey'),
    ('title:something hey', '+title:something hey'),
    ('hey title:something hey person:john', '+title:something +person:john hey hey')
])
def test_query_placeholders(query, expected):
    assert format_query(query) == expected
