# This file is part of the Indico plugins.
# Copyright (C) 2019 - 2025 Various contributors + CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms.fields.simple import BooleanField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.categories.forms import IndicoPasswordField
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin,
                                           PaymentPluginSettingsFormBase)
from indico.web.forms.base import generated_data
from indico.web.forms.validators import HiddenUnless
from indico.web.forms.widgets import SwitchWidget

from indico_payment_stripe import _
from indico_payment_stripe.util import validate_stripe_key


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    stripe_api_key_global = IndicoPasswordField(
        _('Stripe secret API key'),
        [Optional(), validate_stripe_key],
        description=_(
            'Secret API key for the Stripe account. Event managers can override this, but will never see the one '
            'configured here. If left empty, event managers are required to provide their own key. Clearing this field '
            'once events are using Stripe will break payments in these events unless a custom key is set there.'
        ),
        toggle=True,
    )


class EventSettingsFormWithGlobalKey(PaymentEventSettingsFormBase):
    use_custom_key = BooleanField(
        _('Custom Stripe API key'),
        [Optional()],
        default=False,
        description=_('Override the globally configured Stripe API key.'),
        widget=SwitchWidget(),
    )
    stripe_api_key = IndicoPasswordField(
        _('Stripe secret API key'),
        [HiddenUnless('use_custom_key'), DataRequired(), validate_stripe_key],
        description=_('Secret API key for the Stripe account'),
        toggle=True,
    )


class EventSettingsFormNoGlobalKey(PaymentEventSettingsFormBase):
    stripe_api_key = IndicoPasswordField(
        _('Stripe secret API key'),
        [DataRequired(), validate_stripe_key],
        description=_('Secret API key for the Stripe account'),
        toggle=True,
    )

    @generated_data
    def use_custom_key(self):
        return True


class StripePaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Stripe

    Provides a payment method using the Stripe API.
    """

    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'method_name': 'Stripe',
        'stripe_api_key_global': '',
    }
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        'use_custom_key': False,
        'stripe_api_key': None,
    }

    def event_settings_form(self, *args, **kwargs):
        form_cls = (
            EventSettingsFormWithGlobalKey
            if self.settings.get('stripe_api_key_global')
            else EventSettingsFormNoGlobalKey
        )
        return form_cls(*args, **kwargs)

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.svg')

    def get_blueprints(self):
        from indico_payment_stripe.blueprint import blueprint

        return blueprint
