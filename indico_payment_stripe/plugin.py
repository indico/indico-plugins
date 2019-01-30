# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.plugin
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The actual plugin definitions.

"""

from wtforms.fields.core import BooleanField, StringField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (
    PaymentEventSettingsFormBase,
    PaymentPluginMixin,
    PaymentPluginSettingsFormBase,
)

from .blueprint import blueprint
from .utils import _


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
    org_name = StringField(
        _('organization name'),
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
        default='Conference',
        description=_('Name of the event')
    )
    description = StringField(
        _('description'),
        [Optional()],
        default='Payment for conference',
        description=_('A description of the product or service being purchased')
    )
    require_postal_code = BooleanField(
        _('require registrants to input postal code'),
        [Optional()],
        default=False,
        description=_(
            'Whether registrants are required to input their postal code'
            ' when filling the payment form. Setting this to true will decrease'
            ' the chance of the payment being detected as fraudulent.'
        )
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
        'org_name': '',
        'description': '',
    }
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        'pub_key': None,
        'sec_key': None,
        'name': None,
        'description': None,
        'require_postal_code': False,
    }

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        registration = data['registration']
        data['user_email'] = registration.email
        data['handler_url'] = url_for_plugin(
            'payment_stripe.handler',
            registration.locator.uuid,
            _external=True,
        )
