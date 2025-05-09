# This file is part of the Indico plugins.
# Copyright (C) 2019 - 2025 <original contributors tbd>, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

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
    }
    default_event_settings = {
        'enabled': False,
        'use_event_api_keys': False,
        'method_name': None,
        # NOTE: apparently setting a value to `None` here means using the
        #       plugin default and showing it in the event settings form?
        'sec_key': '',
    }

    def init(self):
        super().init()

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        from indico_payment_stripe.blueprint import blueprint
        return blueprint
