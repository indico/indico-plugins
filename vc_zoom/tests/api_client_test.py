# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import base64

import pytest

from indico_vc_zoom.api import ZoomIndicoClient
from indico_vc_zoom.task import refresh_token


@pytest.fixture
def zoom_credentials(zoom_plugin):
    zoom_plugin.settings.set_multi({'account_id': 'acc', 'client_id': 'cid', 'client_secret': 'db-secret'})


@pytest.fixture
def zoom_oauth(mocked_responses):
    mocked_responses.post('https://zoom.us/oauth/token', json={'access_token': 'tok', 'expires_in': 3600,
                                                               'scope': '', 'api_url': 'https://api.zoom.us'})
    return mocked_responses


def _basic_auth(client_id, client_secret):
    return 'Basic ' + base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()


@pytest.mark.usefixtures('db', 'zoom_credentials')
def test_api_client_uses_db_secret_when_config_unset(zoom_oauth):
    zoom_oauth.get('https://api.zoom.us/v2/users/someone', json={})
    ZoomIndicoClient().get_user('someone')
    assert zoom_oauth.calls[0].request.headers['Authorization'] == _basic_auth('cid', 'db-secret')


@pytest.mark.usefixtures('db', 'zoom_credentials')
def test_api_client_prefers_config_secret(zoom_oauth, patch_indico_config):
    patch_indico_config('PLUGIN_VC_ZOOM_CLIENT_SECRET', 'config-secret')
    zoom_oauth.get('https://api.zoom.us/v2/users/someone', json={})
    ZoomIndicoClient().get_user('someone')
    assert zoom_oauth.calls[0].request.headers['Authorization'] == _basic_auth('cid', 'config-secret')


@pytest.mark.usefixtures('db', 'zoom_credentials')
def test_token_refresh_prefers_config_secret(zoom_oauth, patch_indico_config):
    patch_indico_config('PLUGIN_VC_ZOOM_CLIENT_SECRET', 'config-secret')
    refresh_token()
    assert zoom_oauth.calls[0].request.headers['Authorization'] == _basic_auth('cid', 'config-secret')


@pytest.mark.usefixtures('db', 'zoom_plugin')
def test_token_refresh_skips_without_credentials(mocked_responses):
    refresh_token()
    assert not mocked_responses.calls
