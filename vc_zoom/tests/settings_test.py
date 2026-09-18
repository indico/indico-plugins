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


CONFIG_FIELDS = ('account_id', 'client_id', 'client_secret', 'webhook_token')


@pytest.mark.parametrize('field', CONFIG_FIELDS)
@pytest.mark.usefixtures('request_context')
def test_settings_form_editable_when_not_in_config(field):
    form_field = PluginSettingsForm(obj=FormDefaults(**{field: 'db-value'}))[field]
    assert 'disabled' not in str(form_field)
    assert 'db-value' in str(form_field)
    assert PROVIDED_BY_ADMIN not in (form_field.description or '')


@pytest.mark.parametrize('field', CONFIG_FIELDS)
@pytest.mark.usefixtures('request_context')
def test_settings_form_hides_value_when_in_config(field, patch_indico_config):
    patch_indico_config(f'PLUGIN_VC_ZOOM_{field.upper()}', 'config-value')
    form_field = PluginSettingsForm(obj=FormDefaults(**{field: 'db-value'}))[field]
    assert 'disabled' in str(form_field)
    assert form_field.description == PROVIDED_BY_ADMIN
    assert 'db-value' not in str(form_field)
    assert 'config-value' not in str(form_field)
    assert '*****' in str(form_field)


@pytest.mark.parametrize('field', CONFIG_FIELDS)
@pytest.mark.usefixtures('request_context')
def test_settings_form_keeps_stored_value_when_in_config(field, patch_indico_config):
    patch_indico_config(f'PLUGIN_VC_ZOOM_{field.upper()}', 'config-value')
    form = PluginSettingsForm(formdata=MultiDict({'passcode_length': '8'}), obj=FormDefaults(**{field: 'db-value'}),
                              csrf_enabled=False)
    assert form.data[field] == 'db-value'


@pytest.mark.usefixtures('request_context')
def test_settings_form_checks_credentials_with_config_credentials(patch_indico_config, mocked_responses):
    patch_indico_config('PLUGIN_VC_ZOOM_ACCOUNT_ID', 'config-acc')
    patch_indico_config('PLUGIN_VC_ZOOM_CLIENT_ID', 'config-cid')
    patch_indico_config('PLUGIN_VC_ZOOM_CLIENT_SECRET', 'config-secret')
    mocked_responses.post('https://zoom.us/oauth/token', status=401, json={'reason': 'Invalid client'})
    form = PluginSettingsForm(formdata=MultiDict({'passcode_length': '8'}), csrf_enabled=False)
    assert not form.validate()
    assert 'Could not get Zoom token: {"reason": "Invalid client"}' in form.client_secret.errors
    request = mocked_responses.calls[0].request
    assert request.headers['Authorization'] == 'Basic ' + base64.b64encode(b'config-cid:config-secret').decode()
    assert 'account_id=config-acc' in request.url


@pytest.mark.usefixtures('request_context')
def test_settings_form_checks_typed_credentials(mocked_responses):
    mocked_responses.post('https://zoom.us/oauth/token', status=401, json={'reason': 'Invalid client'})
    form = PluginSettingsForm(formdata=MultiDict({'account_id': 'acc', 'client_id': 'cid', 'client_secret': 'typed',
                                                  'passcode_length': '8'}), csrf_enabled=False)
    assert not form.validate()
    assert 'Could not get Zoom token: {"reason": "Invalid client"}' in form.client_secret.errors
    expected_auth = 'Basic ' + base64.b64encode(b'cid:typed').decode()
    assert mocked_responses.calls[0].request.headers['Authorization'] == expected_auth
