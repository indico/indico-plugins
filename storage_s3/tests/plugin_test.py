# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

import hashlib
import hmac

import pytest

from indico.core.storage import StorageError

from indico_storage_s3 import plugin
from indico_storage_s3.storage import DynamicS3Storage, S3Storage
from indico_storage_s3.task import create_bucket


@pytest.fixture(autouse=True)
def mock_boto3(mocker):
    mocker.patch('indico_storage_s3.storage.boto3')


def test_resolve_bucket_name_static():
    storage = plugin.S3Storage('bucket=test')
    assert storage._get_current_bucket_name() == 'test'


@pytest.mark.parametrize(('date', 'name_template', 'expected_name'), (
    ('2018-04-11', 'name-<year>', 'name-2018'),
    ('2018-04-11', 'name-<year>-<month>', 'name-2018-04'),
    ('2018-04-11', 'name-<year>-<week>', 'name-2018-15'),
    ('2018-01-01', 'name-<year>-<week>', 'name-2018-01'),
    ('2019-01-01', 'name-<year>-<week>', 'name-2019-00'),

))
def test_resolve_bucket_name_dynamic(freeze_time, date, name_template, expected_name):
    freeze_time(date)
    storage = plugin.DynamicS3Storage('bucket_template={},bucket_secret=secret'.format(name_template))
    name, token = storage._get_current_bucket_name().rsplit('-', 1)
    assert name == expected_name
    assert token == hmac.new(b'secret', expected_name, hashlib.md5).hexdigest()


class MockConfig(object):
    def __init__(self):
        self.STORAGE_BACKENDS = {'s3': None}


@pytest.mark.usefixtures('app_context')
@pytest.mark.parametrize(('date', 'name_template', 'bucket_created', 'expected_name', 'expected_error'), (
    ('2018-04-11', 'name', False, None, None),
    ('2018-12-01', 'name', False, None, None),
    ('2018-04-11', 'name-<year>', False, None, None),
    ('2018-01-01', 'name-<year>', False, None, None),
    ('2018-12-01', 'name-<month>', False, None, RuntimeError),
    ('2018-12-01', 'name-<week>', False, None, RuntimeError),
    ('2018-12-01', 'name-<month>-<week>', False, None, RuntimeError),
    ('2018-12-01', 'name-<year>', True, 'name-2019', None),
    ('2018-12-01', 'name-<year>-<month>', True, 'name-2019-01', None),
    ('2018-01-01', 'name-<year>-<month>', True, 'name-2018-02', None),
    ('2018-12-03', 'name-<year>-<week>', True, 'name-2018-50', None),
))
def test_dynamic_bucket_creation_task(freeze_time, mocker, date, name_template, bucket_created, expected_name,
                                      expected_error):
    freeze_time(date)
    if '<' in name_template:
        storage = plugin.DynamicS3Storage('bucket_template={},bucket_secret=secret'.format(name_template))
    else:
        storage = plugin.S3Storage('bucket={}'.format(name_template))
    mocker.patch('indico_storage_s3.task.config', MockConfig())
    mocker.patch('indico_storage_s3.task.get_storage', return_value=storage)
    create_bucket_call = mocker.patch.object(plugin.DynamicS3Storage, '_create_bucket')
    if expected_error:
        with pytest.raises(expected_error):
            create_bucket()
    else:
        create_bucket()
    if bucket_created:
        token = hmac.new(b'secret', expected_name, hashlib.md5).hexdigest()
        create_bucket_call.assert_called_with('{}-{}'.format(expected_name, token))
    else:
        assert not create_bucket_call.called


def test_static_bucket_name_too_long():
    S3Storage('bucket=test' + 'x'*59)
    with pytest.raises(StorageError):
        S3Storage('bucket=test' + 'x'*60)


def test_dynamic_bucket_name_too_long():
    s = DynamicS3Storage('bucket_secret=secret,bucket_template=test-<year>' + 'x'*37)
    assert len(s._get_current_bucket_name()) == 63
    s = DynamicS3Storage('bucket_secret=secret,bucket_template=test-<year>-<month>' + 'x'*34)
    assert len(s._get_current_bucket_name()) == 63
    with pytest.raises(StorageError):
        DynamicS3Storage('bucket_secret=secret,bucket_template=test-<year>' + 'x' * 38)
    with pytest.raises(StorageError):
        DynamicS3Storage('bucket_secret=secret,bucket_template=test-<year>-<month>' + 'x' * 35)
