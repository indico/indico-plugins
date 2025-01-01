# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest
from prometheus_client.parser import text_string_to_metric_families

from indico.core.plugins import plugin_engine


@pytest.fixture
def get_metrics(make_test_client):
    def _get_metrics(token=None, expect_status_code=200):
        client = make_test_client()
        resp = client.get('/metrics', headers=({'Authorization': f'Bearer {token}'} if token else {}))
        assert resp.status_code == expect_status_code

        if resp.status_code == 200:
            return {
                metric.name: metric.samples[0].value
                for metric in text_string_to_metric_families(resp.data.decode('utf-8'))
            }, resp.headers
        else:
            return None
    return _get_metrics


@pytest.fixture
def enable_plugin():
    plugin_engine.get_plugin('prometheus').settings.set('enabled', True)


@pytest.mark.usefixtures('db')
def test_endpoint_disabled_by_default(get_metrics):
    get_metrics(expect_status_code=503)


@pytest.mark.usefixtures('db', 'enable_plugin')
def test_endpoint_works(get_metrics):
    get_metrics()


@pytest.mark.usefixtures('db', 'enable_plugin')
def test_endpoint_empty(get_metrics):

    metrics = get_metrics()[0]

    assert metrics['indico_num_users'] == 1.0
    assert metrics['indico_num_active_users'] == 0.0
    assert metrics['indico_num_events'] == 0.0
    assert metrics['indico_num_categories'] == 1.0
    assert metrics['indico_num_attachment_files'] == 0.0
    assert metrics['indico_num_active_attachment_files'] == 0.0


@pytest.mark.usefixtures('db', 'enable_plugin')
def test_endpoint_cached(get_metrics, create_event):
    metrics, headers = get_metrics()
    assert metrics['indico_num_events'] == 0.0
    assert headers['X-Cached'] == 'no'

    # create an event
    create_event(title='Test event #1')

    metrics, headers = get_metrics()

    # cached information should show zero events
    assert metrics['indico_num_events'] == 0.0
    assert headers['X-Cached'] == 'yes'


@pytest.mark.usefixtures('db', 'enable_plugin')
def test_endpoint_returning_data(get_metrics, create_event):
    # create an event
    create_event(title='Test event #1')

    metrics = get_metrics()[0]
    assert metrics['indico_num_users'] == 2.0
    assert metrics['indico_num_active_users'] == 0.0
    assert metrics['indico_num_events'] == 1.0
    assert metrics['indico_num_categories'] == 2.0
    assert metrics['indico_num_attachment_files'] == 0.0
    assert metrics['indico_num_active_attachment_files'] == 0.0


@pytest.mark.usefixtures('db', 'enable_plugin')
def test_endpoint_authentication(get_metrics):
    plugin_engine.get_plugin('prometheus').settings.set('token', 'schnitzel_with_naughty_rice')
    get_metrics(expect_status_code=401)

    get_metrics(token='schnitzel_with_naughty_rice')
    get_metrics(token='spiritual_codfish', expect_status_code=401)
