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
from indico.web.forms.validators import HiddenUnless, UsedIf

from .blueprint import blueprint
from .utils import _, conv_to_stripe_amount


class PluginSettingsForm(PaymentPluginSettingsFormBase):

    pub_key = StringField(
        _('publishable key'),
        [DataRequired()],
        description=_(
            'Publishable API key for the stripe.com account. Event managers can'
            ' override this.'
        )
    )
    sec_key = StringField(
        _('secret key'),
        [DataRequired()],
        description=_(
            'Secret API key for the stripe.com account. Event managers can'
            ' override this.'
        )
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

    use_event_api_keys = BooleanField(
        _('use custom API keys'),
        [Optional()],
        default=False,
        description=_(
            'Check this box to override the organization Stripe API keys.'
        )
    )
    pub_key = StringField(
        _('publishable key'),
        [
            HiddenUnless('use_event_api_keys'),
            UsedIf(lambda form, _: form.use_event_api_keys.data),
            DataRequired(),
        ],
        description=_('Publishable API key for the stripe.com account')
    )
    sec_key = StringField(
        _('secret key'),
        [
            HiddenUnless('use_event_api_keys'),
            UsedIf(lambda form, _: form.use_event_api_keys.data),
            DataRequired(),
        ],
        description=_('Secret API key for the stripe.com account')
       )
    org_name = StringField(
        _('organizer name'),
        [Optional()],
        default='Organization',
        description=_('Name of the event organizer')
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
        'use_event_api_keys': False,
        'method_name': None,
        # NOTE: apparently setting a value to `None` here means using the
        #       plugin default and showing it in the event settings form?
        'pub_key': '',
        'sec_key': '',
        'org_name': None,
        'description': None,
        'require_postal_code': False,
    }

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        registration = data['registration']
        data['stripe_amount'] = conv_to_stripe_amount(
            registration.price,
            registration.currency,
        )
        data['user_email'] = registration.email
        data['handler_url'] = url_for_plugin(
            'payment_stripe.handler',
            registration.locator.uuid,
            _external=True,
        )

        data['pub_key'] = (
            data['event_settings']['pub_key']
            if data['event_settings']['use_event_api_keys'] else
            data['settings']['pub_key']
        )
