# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask_pluginengine import render_plugin_template

from wtforms.fields.core import StringField, BooleanField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin,
                                           PaymentPluginSettingsFormBase)
from indico.util.string import remove_accents, unicode_to_ascii
from indico.web.forms.validators import UsedIf
from indico.web.forms.widgets import SwitchWidget

from indico_payment_paypal import _
from indico_payment_paypal.blueprint import blueprint
from indico_payment_paypal.util import validate_business

from babel.numbers import format_currency
from flask import session

class PluginSettingsForm(PaymentPluginSettingsFormBase):
    url = URLField(_('API URL'), [DataRequired()], description=_('URL of the PayPal HTTP API.'))
    business = StringField(_('Business'), [Optional(), validate_business],
                           description=_('The default PayPal ID or email address associated with a PayPal account.'
                                         'Event managers will be able to override this.'))
    itemize = BooleanField(_('Itemize PayPal Cart'), [Optional()], widget=SwitchWidget(),
                           description=_('Check to itemize the PayPal cart'))


class EventSettingsForm(PaymentEventSettingsFormBase):
    business = StringField(_('Business'), [UsedIf(lambda form, _: form.enabled.data), DataRequired(),
                                           validate_business],
                           description=_('The PayPal ID or email address associated with a PayPal account.'))
    itemize = BooleanField(_('Itemize PayPal Cart'), [Optional()], widget=SwitchWidget(),
                           description=_('Check to itemize the PayPal cart'))


class PaypalPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """PayPal

    Provides a payment method using the PayPal IPN API.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {'method_name': 'PayPal',
                        'url': 'https://www.paypal.com/cgi-bin/webscr',
                        'business': '',
                        'itemize': False}
    default_event_settings = {'enabled': False,
                              'method_name': None,
                              'business': None,
                              'itemize': False}

    def init(self):
        super(PaypalPaymentPlugin, self).init()
        self.template_hook('event-manage-payment-plugin-before-form', self._get_encoding_warning)

    def create_choice_data(self, data_list, title1, title2, price, quantity, price_info):
        choice = {'title': '{} {dash} {}'.format(title1, title2, dash='-' if title2 else ''),
                  'price': format_currency(price, '', u'#0.00', locale=session.lang or 'en_GB'),
                  'quantity': quantity,
                  'price_info': price_info}
        data_list.append(choice)

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        event = data['event']
        registration = data['registration']
        data['item_name'] = '{}: registration for {}'.format(
            unicode_to_ascii(remove_accents(registration.full_name, reencode=False)),
            unicode_to_ascii(remove_accents(event.title, reencode=False))
        )
        data['return_url'] = url_for_plugin('payment_paypal.success', registration.locator.uuid, _external=True)
        data['cancel_url'] = url_for_plugin('payment_paypal.cancel', registration.locator.uuid, _external=True)
        data['notify_url'] = url_for_plugin('payment_paypal.notify', registration.locator.uuid, _external=True)

# PayPal Itemized cart get all billable items
        itemized_data = []
        if registration.base_price:
            self.create_choice_data(itemized_data, 'Registration Fee', '', registration.base_price, 1,
                                    registration.base_price_info)

        for section, fields in registration.summary_data.iteritems():
            for field, regdata in fields.iteritems():
                friendly_data  = regdata.friendly_data
                versioned_data = regdata.field_data.versioned_data
                unversioned_data = regdata.field_data.field.data
                if regdata.field_data.field.input_type == 'accommodation' and friendly_data:
                    billable_choices = [x for x in versioned_data['choices'] if x['id'] in regdata.data['choice'] 
                                        and x['is_billable']]
                    if billable_choices:
                        if not friendly_data['is_no_accommodation']:
                            self.create_choice_data(itemized_data, section.title, friendly_data['choice'],
                                                    billable_choices[0]['price'], friendly_data['nights'],
                                                    billable_choices[0]['price_info'])
                elif regdata.field_data.field.input_type == 'single_choice':
                    billable_choices = [x for x in versioned_data['choices'] if x['id'] in regdata.data
                                        and x['is_billable']]
                    if billable_choices:
                        self.create_choice_data(itemized_data, field.title,
                                                unversioned_data['captions'][billable_choices[0]['id']],
                                                billable_choices[0]['price'], regdata.data[billable_choices[0]['id']],
                                                billable_choices[0]['price_info'])
                elif regdata.field_data.field.input_type == 'multi_choice':
                    billable_choices = [x for x in versioned_data['choices'] if x['id'] in regdata.data
                                        and x['is_billable']]
                    if billable_choices:
                        for bc in billable_choices:
                            self.create_choice_data(itemized_data, field.title, unversioned_data['captions'][bc['id']],
                                                    bc['price'], regdata.data[bc['id']], bc['price_info'])
                else:
                    if regdata.price:
                        self.create_choice_data(itemized_data, section.title, field.title, versioned_data['price'],
                                                regdata.data if regdata.field_data.field.input_type == 'number'
                                                else 1, versioned_data['price_info'])
        data['itemized_data'] = itemized_data

    def _get_encoding_warning(self, plugin=None, event=None):
        if plugin == self:
            return render_plugin_template('event_settings_encoding_warning.html')
