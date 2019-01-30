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
    pub_key = StringField(_('publishable key'), [DataRequired()], description_('Publishable API key for the stripe.com account'))
    sec_key = StringField(_('secret key'), [DataRequired()], description_('Secret API key for the stripe.com account'))
    data_name = StringField(_('data name'), [Optional()], description_('Name of the organization'))
    data_description = StringField(_('data description'), [Optional()], description_(' A description of the product or service being purchased'))


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
