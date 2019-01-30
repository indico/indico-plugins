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
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin, PaymentPluginSettingsFormBase)
from indico.util.i18n import make_bound_gettext

from indico_payment_stripe.blueprint import blueprint

_ = make_bound_gettext('payment_stripe')


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
        'pub_key': '',
        'sec_key': '',
        'data_name': '',
        'data_description': '',
    }
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        'business': None,
    }

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        data['handler_url'] = url_for_plugin('payment_stripe.handler')