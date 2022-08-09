# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2022 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import requests
from requests.exceptions import RequestException
from wtforms.fields import BooleanField, StringField
from wtforms.validators import DataRequired

from indico.core.plugins import IndicoPlugin
from indico.modules.events.registration.plugins import CaptchaPluginMixin
from indico.web.forms.base import IndicoForm
from indico.web.forms.widgets import SwitchWidget
from indico.web.views import WPBase

from indico_recaptcha import _


class ReCaptchaSettingsForm(IndicoForm):
    enabled = BooleanField(_('Enabled'), widget=SwitchWidget(), description=_('Whether to enable the access overrides'))
    site_key = StringField(_('Site key'), [DataRequired()],
                           description=_('The site key available in the reCAPTCHA admin dashboard'))
    secret_key = StringField(_('Secret key'), [DataRequired()],
                             description=_('The secret key available in the reCAPTCHA admin dashboard'))


class ReCaptchaPlugin(CaptchaPluginMixin, IndicoPlugin):
    """Google reCAPTCHA

    Provides ReCAPTCHA check for registrations.
    The plugin needs the site key and secret key to work properly which
    you can obtain from the reCAPTCHA admin dashboard.
    """

    configurable = True
    settings_form = ReCaptchaSettingsForm
    default_settings = {
        'enabled': False,
        'site_key': '',
        'secret_key': '',
    }

    def init(self):
        super().init()
        self.inject_bundle('main.js', WPBase, condition=lambda: self.settings.get('enabled'))
        self.inject_bundle('main.css', WPBase, condition=lambda: self.settings.get('enabled'))

    def is_captcha_available(self):
        return self.settings.get('enabled') and bool(self.settings.get('site_key'))

    def validate_captcha(self, answer):
        secret = self.settings.get('secret_key')
        resp = requests.post('https://www.google.com/recaptcha/api/siteverify',
                             data={'secret': secret, 'response': answer})
        try:
            resp.raise_for_status()
        except RequestException as exc:
            self.logger.error('Failed to validate CAPTCHA: %s', exc.response.text)
            return False
        return resp.json()['success']

    def get_captcha_settings(self):
        return {'siteKey': self.settings.get('site_key')}
