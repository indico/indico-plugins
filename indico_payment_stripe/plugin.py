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
    token = StringField(_('token'), [DataRequired()], description_('Publishable API key for the account'))
    data-name = StringField(_('data-name'), [Optional()], description_('Name of the organization'))
    data-description = StringField(_('data-description'), [Optional()], description_(' A description of the product or service being purchased'))


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
