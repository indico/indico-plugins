from wtforms.fields.simple import BooleanField, StringField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin,
                                           PaymentPluginSettingsFormBase)
from indico.web.forms.validators import HiddenUnless, UsedIf
from indico.web.forms.widgets import SwitchWidget

from indico_payment_stripe import _


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    sec_key = StringField(
        _('Secret key'),
        [DataRequired()],
        description=_(
            'Secret API key for the stripe.com account. Event managers can'
            ' override this.'
        )
    )
    org_name = StringField(
        _('Organization name'),
        [Optional()],
        description=_('Name of the organization')
    )
    description = StringField(
        _('Description'),
        [Optional()],
        description=_('A description of the product or service being purchased')
    )


class EventSettingsForm(PaymentEventSettingsFormBase):
    use_event_api_keys = BooleanField(
        _('Use event API keys'),
        [Optional()],
        default=False,
        description=_(
            'Override the organization Stripe API keys.'
        ),
        widget=SwitchWidget(),
    )
    sec_key = StringField(
        _('Secret key'),
        [
            HiddenUnless('use_event_api_keys'),
            UsedIf(lambda form, _: form.use_event_api_keys.data),
            DataRequired(),
        ],
        description=_('Secret API key for the stripe.com account')
    )
    org_name = StringField(
        _('Organizer name'),
        [Optional()],
        default='Organization',
        description=_('Name of the event organizer')
    )
    description = StringField(
        _('Description'),
        [Optional()],
        default='Payment for conference',
        description=_('A description of the product or service being purchased')
    )
    require_postal_code = BooleanField(
        _('Require postal code input'),
        [Optional()],
        default=False,
        description=_(
            'Require registrants to input their postal code when filling the'
            ' payment form. Enabling this will decrease the chance of the'
            ' payment being marked as fraudulent.'
        ),
        widget=SwitchWidget(),
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
        'sec_key': '',
        'org_name': None,
        'description': None,
        'require_postal_code': False,
    }

    def init(self):
        super().init()

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        from indico_payment_stripe.blueprint import blueprint
        return blueprint
