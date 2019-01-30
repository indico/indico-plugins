# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.plugin
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin
from indico.modules.events.payment import (
    PaymentEventSettingsFormBase, PaymentPluginMixin,
    PaymentPluginSettingsFormBase
)
from indico_payment_paypal import _
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin, PaymentPluginSettingsFormBase)



class PluginSettingsForm(PaymentPluginSettingsFormBase):
    pub_key = StringField(_('publishable key'), [DataRequired()], description=_('Publishable API key for the stripe.com account'))
    sec_key = StringField(_('secret key'), [DataRequired()], description=_('Secret API key for the stripe.com account'))
    data_name = StringField(_('data name'), [Optional()], description=_('Name of the organization'))
    data_description = StringField(_('data description'), [Optional()], description=_(' A description of the product or service being purchased'))


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
