# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import mock
import pytest
from freezegun import freeze_time

import indico_storage_s3.plugin as plugin
from indico_storage_s3.task import create_bucket


@pytest.mark.parametrize(('date', 'name_template', 'expected_name'), (
    ('2018-04-11', 'name', 'name'),
    ('2018-04-11', 'name-<year>', 'name-2018'),
    ('2018-04-11', 'name-<year>-<month>', 'name-2018-04'),
    ('2018-04-11', 'name-<year>-<week>', 'name-2018-15'),
    ('2018-01-01', 'name-<year>-<week>', 'name-2018-01'),
    ('2019-01-01', 'name-<year>-<week>', 'name-2019-00'),

))
@mock.patch.object(plugin.S3Storage, '__init__', lambda self: None)
def test_resolve_bucket_name(date, name_template, expected_name):
    with freeze_time(date):
        storage = plugin.S3Storage()
        assert storage.get_bucket_name(name_template) == expected_name


@mock.create_autospec
def fake_bucket_created(name, replace_placeholders=True):
    pass


@pytest.mark.usefixtures('app_context')
@pytest.mark.parametrize(('date', 'name_template', 'bucket_created', 'expected_name'), (
    ('2018-04-11', 'name', False, None),
    ('2018-12-01', 'name', False, None),
    ('2018-04-11', 'name-<year>', False, None),
    ('2018-01-01', 'name-<year>', False, None),
    ('2018-12-01', 'name-<year>-<week>', False, None),
    ('2018-12-02', 'name-<year>-<week>', False, None),
    ('2018-02-10', 'name-<year>-<month>', False, None),
    ('2018-12-01', 'name-<year>', True, 'name-2019'),
    ('2018-12-01', 'name-<year>-<month>', True, 'name-2019-01'),
    ('2018-01-01', 'name-<year>-<month>', True, 'name-2018-02'),
    ('2018-12-03', 'name-<year>-<week>', True, 'name-2018-50'),
))
def test_dynamic_bucket_creation_task(date, name_template, bucket_created, expected_name):
    with freeze_time(date), \
         mock.patch.object(plugin.S3Storage, '__init__', lambda self: None),\
         mock.patch.object(plugin.S3Storage, 'get_bucket_name', return_value=name_template),\
         mock.patch('indico_storage_s3.task.get_storage', return_value=plugin.S3Storage()),\
         mock.patch.object(plugin.S3Storage, 'create_bucket', fake_bucket_created) as create_bucket_call:
        create_bucket()
    if bucket_created:
        create_bucket_call.assert_called_with(mock.ANY, expected_name)
    else:
        assert not create_bucket_call.called
