# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.plugin
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from indico.core.plugins import IndicoPlugin
from indico.modules.events.payment import (
    PaymentEventSettingsFormBase, PaymentPluginMixin,
    PaymentPluginSettingsFormBase
)


class PluginSettingsForm(PaymentPluginSettingsFormBase):

    pass


class EventSettingsForm(PaymentEventSettingsFormBase):

    pass


class StripePaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Stripe

    Provides a payment method using the Stripe API.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {
        'method_name': 'Stripe',
        'url': 'https://stripe.com',
        'business': '',
    }
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        'business': None,
    }
