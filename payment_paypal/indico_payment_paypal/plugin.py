# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from decimal import Decimal

from flask_pluginengine import render_plugin_template
from wtforms.fields import DecimalField, StringField, URLField
from wtforms.validators import DataRequired, NumberRange, Optional
from wtforms.widgets import NumberInput

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin,
                                           PaymentPluginSettingsFormBase)
from indico.util.string import remove_accents, str_to_ascii
from indico.web.forms.validators import UsedIf

from indico_payment_paypal import _
from indico_payment_paypal.blueprint import blueprint
from indico_payment_paypal.util import validate_business


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    url = URLField(_('API URL'), [DataRequired()], description=_('URL of the PayPal HTTP API.'))
    business = StringField(_('Business'), [Optional(), validate_business],
                           description=_('The default PayPal ID or email address associated with a PayPal account. '
                                         'Event managers will be able to override this.'))


class EventSettingsForm(PaymentEventSettingsFormBase):
    @property
    def data(self):
        return {k: str(v) for k, v in super().data.items()}

    business = StringField(_('Business'), [UsedIf(lambda form, _: form.enabled.data), DataRequired(),
                                           validate_business],
                           description=_('The PayPal ID or email address associated with a PayPal account.'))

    paypal_fixed_fee = DecimalField(_('PayPal Fixed Transaction fee'),
                              [NumberRange(min=Decimal('0.00'), max=999999999.99), Optional()], 
                              filters=[lambda x: Decimal(x) if x is not None else 0], widget=NumberInput(step='0.01'),
                              description=_('The paypal fixed fee applied to the transaction.'))
    paypal_percent_fee = DecimalField(_('PayPal Percentage Transaction fee'),
                              [NumberRange(min=Decimal('0.00'), max=999999999.99), Optional()],
                              filters=[lambda x: Decimal(x) if x is not None else 0], widget=NumberInput(step='0.01'),
                              description=_('The paypal percentage fee applied to the transaction %.'))


class PaypalPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """PayPal

    Provides a payment method using the PayPal IPN API.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {'method_name': 'PayPal',
                        'url': 'https://www.paypal.com/cgi-bin/webscr',
                        'business': ''}
    default_event_settings = {'enabled': False,
                              'method_name': None,
                              'business': None,
                              'paypal_fixed_fee': Decimal('0.0'),
                              'paypal_percent_fee': Decimal('0.0')}

    def init(self):
        super().init()
        self.template_hook('event-manage-payment-plugin-before-form', self._get_encoding_warning)

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        event = data['event']
        event_settings_form = data['event_settings']
        registration = data['registration']
        plain_name = str_to_ascii(remove_accents(registration.full_name))
        plain_title = str_to_ascii(remove_accents(event.title))
        data['item_name'] = f'{plain_name}: registration for {plain_title}'
        data['return_url'] = url_for_plugin('payment_paypal.success', registration.locator.uuid, _external=True)
        data['cancel_url'] = url_for_plugin('payment_paypal.cancel', registration.locator.uuid, _external=True)
        data['notify_url'] = url_for_plugin('payment_paypal.notify', registration.locator.uuid, _external=True)
        # Add Paypal fees
        amount = Decimal(data['amount'])
        data['paypal_amount'] = amount
        paypal_fixed_fee = Decimal(event_settings_form['paypal_fixed_fee'])
        paypal_percent_fee = Decimal(event_settings_form['paypal_percent_fee']) 
        amount_with_paypal_fees = Decimal(round(( amount + paypal_fixed_fee ) / ( 1 - ( paypal_percent_fee / 100 )),2))
        data['amount'] = amount_with_paypal_fees
        fees = amount_with_paypal_fees - amount
        data['paypal_fees'] = str(amount_with_paypal_fees - amount)

    def _get_encoding_warning(self, plugin=None, event=None):
        if plugin == self:
            return render_plugin_template('event_settings_encoding_warning.html')
