# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2026 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import base64

import pytest
from werkzeug.datastructures import MultiDict

from indico.web.forms.base import FormDefaults

from indico_vc_zoom.plugin import PluginSettingsForm


PROVIDED_BY_ADMIN = 'This value has been provided by the system administrator.'


@pytest.mark.parametrize('field', ('client_secret', 'webhook_token'))
@pytest.mark.usefixtures('request_context')
def test_settings_form_editable_secret_when_not_in_config(field):
    assert 'disabled' not in str(PluginSettingsForm()[field])
    assert PROVIDED_BY_ADMIN not in (PluginSettingsForm()[field].description or '')


@pytest.mark.parametrize('field', ('client_secret', 'webhook_token'))
@pytest.mark.usefixtures('request_context')
def test_settings_form_disables_secret_when_in_config(field, patch_indico_config):
    patch_indico_config(f'PLUGIN_VC_ZOOM_{field.upper()}', 'config-value')
    form_field = PluginSettingsForm()[field]
    assert 'disabled' in str(form_field)
    assert form_field.description == PROVIDED_BY_ADMIN


@pytest.mark.usefixtures('request_context')
def test_settings_form_keeps_stored_secret_when_in_config(patch_indico_config):
    patch_indico_config('PLUGIN_VC_ZOOM_CLIENT_SECRET', 'config-secret')
    form = PluginSettingsForm(formdata=MultiDict({'account_id': 'acc', 'client_id': 'cid'}),
                              obj=FormDefaults(client_secret='db-secret'), csrf_enabled=False)
    assert form.data['client_secret'] == 'db-secret'


@pytest.mark.usefixtures('request_context')
def test_settings_form_checks_credentials_with_config_secret(patch_indico_config, mocked_responses):
    patch_indico_config('PLUGIN_VC_ZOOM_CLIENT_SECRET', 'config-secret')
    mocked_responses.post('https://zoom.us/oauth/token', status=401, json={'reason': 'Invalid client'})
    form = PluginSettingsForm(formdata=MultiDict({'account_id': 'acc', 'client_id': 'cid', 'passcode_length': '8'}),
                              csrf_enabled=False)
    assert not form.validate()
    assert 'Could not get Zoom token: {"reason": "Invalid client"}' in form.client_secret.errors


@pytest.mark.usefixtures('request_context')
def test_settings_form_checks_typed_credentials(mocked_responses):
    mocked_responses.post('https://zoom.us/oauth/token', status=401, json={'reason': 'Invalid client'})
    form = PluginSettingsForm(formdata=MultiDict({'account_id': 'acc', 'client_id': 'cid', 'client_secret': 'typed',
                                                  'passcode_length': '8'}), csrf_enabled=False)
    assert not form.validate()
    assert 'Could not get Zoom token: {"reason": "Invalid client"}' in form.client_secret.errors
    expected_auth = 'Basic ' + base64.b64encode(b'cid:typed').decode()
    assert mocked_responses.calls[0].request.headers['Authorization'] == expected_auth
