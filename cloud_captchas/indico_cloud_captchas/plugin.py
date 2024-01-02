# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import requests
from requests.exceptions import HTTPError, RequestException
from wtforms.fields import StringField
from wtforms.validators import DataRequired

from indico.core.plugins import IndicoPlugin
from indico.modules.api.forms import IndicoEnumSelectField
from indico.modules.core.plugins import CaptchaPluginMixin
from indico.modules.users import EnumConverter
from indico.util.enum import RichIntEnum
from indico.web.forms.base import IndicoForm
from indico.web.forms.validators import HiddenUnless
from indico.web.views import WPBase

from indico_cloud_captchas import _


class CaptchaProvider(RichIntEnum):
    __titles__ = [_("None (use Indico's built-in CAPTCHA)"), 'reCAPTCHA', 'hCaptcha']
    none = 0
    recaptcha = 1
    hcaptcha = 2


class CloudCaptchasSettingsForm(IndicoForm):
    provider = IndicoEnumSelectField(
        _('Type'), enum=CaptchaProvider,
        description=_('Select which CAPTCHA provider you want to use')
    )
    # recaptcha
    recaptcha_site_key = StringField(
        _('reCAPTCHA site key'),
        [HiddenUnless('provider', CaptchaProvider.recaptcha, preserve_data=True), DataRequired()],
        description=_('The site key available in the reCAPTCHA admin dashboard')
    )
    recaptcha_secret_key = StringField(
        _('reCAPTCHA secret key'),
        [HiddenUnless('provider', CaptchaProvider.recaptcha, preserve_data=True), DataRequired()],
        description=_('The secret key available in the reCAPTCHA admin dashboard')
    )
    # hcaptcha
    hcaptcha_site_key = StringField(
        _('hCaptcha site key'),
        [HiddenUnless('provider', CaptchaProvider.hcaptcha, preserve_data=True), DataRequired()],
        description=_('The site key available in the hCaptcha admin dashboard')
    )
    hcaptcha_secret_key = StringField(
        _('hCAPTCHA secret key'),
        [HiddenUnless('provider', CaptchaProvider.hcaptcha, preserve_data=True), DataRequired()],
        description=_('The secret key available in the hCaptcha admin dashboard')
    )


class CloudCaptchasPlugin(CaptchaPluginMixin, IndicoPlugin):
    """Cloud CAPTCHAs

    Replaces Indico's default CAPTCHA with reCAPTCHA or hCaptcha.
    """

    configurable = True
    settings_form = CloudCaptchasSettingsForm
    default_settings = {
        'provider': CaptchaProvider.none,
        'recaptcha_site_key': '',
        'recaptcha_secret_key': '',
        'hcaptcha_site_key': '',
        'hcaptcha_secret_key': '',
    }
    settings_converters = {
        'provider': EnumConverter(CaptchaProvider),
    }

    def init(self):
        super().init()
        self.inject_bundle('main.js', WPBase, condition=lambda: self.settings.get('provider') != CaptchaProvider.none)
        self.inject_bundle('main.css', WPBase, condition=lambda: self.settings.get('provider') != CaptchaProvider.none)

    def is_captcha_available(self):
        provider = self.settings.get('provider')
        if provider == CaptchaProvider.recaptcha:
            return bool(self.settings.get('recaptcha_site_key') and self.settings.get('recaptcha_secret_key'))
        elif provider == CaptchaProvider.hcaptcha:
            return bool(self.settings.get('hcaptcha_site_key') and self.settings.get('hcaptcha_secret_key'))
        return False

    def _validate_recaptcha(self, answer):
        data = {
            'secret': self.settings.get('recaptcha_secret_key'),
            'response': answer
        }
        if resp := self._validate_http_post('https://www.google.com/recaptcha/api/siteverify', data):
            return resp.json()['success']
        return False

    def _validate_hcaptcha(self, answer):
        data = {
            'sitekey': self.settings.get('hcaptcha_site_key'),
            'secret': self.settings.get('hcaptcha_secret_key'),
            'response': answer
        }
        if resp := self._validate_http_post('https://hcaptcha.com/siteverify', data):
            return resp.json()['success']
        return False

    def _validate_http_post(self, url, data):
        try:
            resp = requests.post(url, data=data)
            resp.raise_for_status()
        except HTTPError as exc:
            self.logger.error('Failed to validate CAPTCHA: %s', exc.response.text)
            return None
        except RequestException as exc:
            self.logger.error('Failed to validate CAPTCHA: %s', exc)
            return None
        return resp

    def validate_captcha(self, answer):
        if self.settings.get('provider') == CaptchaProvider.recaptcha:
            return self._validate_recaptcha(answer)
        elif self.settings.get('provider') == CaptchaProvider.hcaptcha:
            return self._validate_hcaptcha(answer)
        # should never happen
        return False

    def get_captcha_settings(self):
        if self.settings.get('provider') == CaptchaProvider.recaptcha:
            return {
                'siteKey': self.settings.get('recaptcha_site_key'),
                'hCaptcha': False,
            }
        elif self.settings.get('provider') == CaptchaProvider.hcaptcha:
            return {
                'siteKey': self.settings.get('hcaptcha_site_key'),
                'hCaptcha': True,
            }
