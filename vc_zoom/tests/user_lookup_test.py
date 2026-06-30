# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest

from indico_vc_zoom.util import find_enterprise_email, preload_zoom_account_directory


@pytest.fixture
def zoom_api_list_users(zoom_api, mocker):
    list_users = mocker.patch('indico_vc_zoom.api.ZoomIndicoClient.list_users')
    list_users.side_effect = [
        {'users': [{'email': 'Alice@MegaCorp.xyz'}, {'email': 'bob@megacorp.xyz'}], 'next_page_token': 'page-2'},
        {'users': [{'email': 'carol@megacorp.xyz'}], 'next_page_token': ''},
    ]
    return list_users


@pytest.mark.usefixtures('request_context', 'db')
def test_preload_zoom_account_directory_pages_list_users(zoom_api, zoom_api_list_users):
    directory = preload_zoom_account_directory()

    assert directory == {'alice@megacorp.xyz', 'bob@megacorp.xyz', 'carol@megacorp.xyz'}
    assert zoom_api_list_users.call_count == 2
    zoom_api['get_user'].assert_not_called()


@pytest.mark.usefixtures('request_context', 'db')
def test_find_enterprise_email_resolves_against_directory(zoom_api, zoom_api_list_users, create_user):
    user = create_user(2, email='alice@megacorp.xyz')
    preload_zoom_account_directory()

    assert find_enterprise_email(user) == 'alice@megacorp.xyz'
    zoom_api['get_user'].assert_not_called()


@pytest.mark.usefixtures('request_context', 'db')
def test_find_enterprise_email_probes_zoom_without_directory(zoom_api, create_user):
    user = create_user(2, email='alice@megacorp.xyz')

    assert find_enterprise_email(user) == 'alice@megacorp.xyz'
    assert zoom_api['get_user'].called
