# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.plugin
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from wtforms.fields.core import StringField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (
    PaymentEventSettingsFormBase,
    PaymentPluginMixin,
    PaymentPluginSettingsFormBase,
)
from indico.util.i18n import make_bound_gettext

from .blueprint import blueprint

_ = make_bound_gettext('payment_stripe')


class PluginSettingsForm(PaymentPluginSettingsFormBase):

    pub_key = StringField(
        _('publishable key'),
        [DataRequired()],
        description=_('Publishable API key for the stripe.com account')
    )
    sec_key = StringField(
        _('secret key'),
        [DataRequired()],
        description=_('Secret API key for the stripe.com account')
       )
    name = StringField(
        _('name'),
        [Optional()],
        description=_('Name of the organization')
    )
    description = StringField(
        _('description'),
        [Optional()],
        description=_('A description of the product or service being purchased')
    )


class EventSettingsForm(PaymentEventSettingsFormBase):

    pub_key = StringField(
        _('publishable key'),
        [DataRequired()],
        description=_('Publishable API key for the stripe.com account')
    )
    sec_key = StringField(
        _('secret key'),
        [DataRequired()],
        description=_('Secret API key for the stripe.com account')
       )
    name = StringField(
        _('name'),
        [Optional()],
        description=_('Name of the organization')
    )
    description = StringField(
        _('description'),
        [Optional()],
        description=_('A description of the product or service being purchased')
    )


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
        'name': '',
        'description': '',
    }
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        'pub_key': None,
        'sec_key': None,
        'name': None,
        'description': None,
    }

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        registration = data['registration']
        data['handler_url'] = url_for_plugin(
            'payment_stripe.handler',
            registration.locator.uuid,
            _external=True,
        )
