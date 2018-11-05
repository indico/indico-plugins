# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

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

class PluginSettingsForm(PaymentPluginSettingsFormBase):
    url = URLField(_('API URL'), [DataRequired()], description=_('URL of the PayPal HTTP API.'))
    business = StringField(_('Business'), [Optional(), validate_business],
                           description=_('The default PayPal ID or email address associated with a PayPal account. '
                                         'Event managers will be able to override this.'))
    itemize = BooleanField(_('Itemize PayPal Cart'), [Optional()], widget=SwitchWidget(), description=_('Check to itemize the PayPal cart'))

class EventSettingsForm(PaymentEventSettingsFormBase):
    business = StringField(_('Business'), [UsedIf(lambda form, _: form.enabled.data), DataRequired(), validate_business],
                           description=_('The PayPal ID or email address associated with a PayPal account.'))
    itemize = BooleanField(_('Itemize PayPal Cart'), [Optional()], widget=SwitchWidget(), description=_('Check to itemize the PayPal cart'))

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

# ##################################################
# PayPal Itemized cart get the billable items
        itemized_data = []
        ii = 1
        paypal_data = ""
        if registration.base_price:
            choice = {}
            choice['title']       = 'Registration Fee'
            choice['price']       = format_currency(registration.base_price, '', u'#0.00', locale='en_US') 
            choice['quantity']    = 1
            choice['price_total'] = choice['price']
            choice['price_info']  = registration.base_price_info
            choice['itemNum']     = ii
            itemized_data.append(choice)

        for section, fields in registration.summary_data.iteritems():	# if not section.is_manager_only:
            sectionTitle = section.title
            
            for field, regdata in fields.iteritems():	# if regdata.friendly_data:
                friendly_data  = regdata.friendly_data
                versioned_data = regdata.field_data.versioned_data
                unversioned_data = regdata.field_data.field.data
                fieldTitle = field.title
            
                choice = {}
                if regdata.field_data.field.input_type == 'accommodation' and friendly_data:
                    billable_choices = [x for x in versioned_data['choices'] if x['id'] in regdata.data['choice']  and x['is_billable']]
                    if billable_choices:
                        if not friendly_data['is_no_accommodation']:
                            ii = ii + 1
                            choice = {}
                            choice['title']       = fieldTitle + ' - ' + friendly_data['choice']
                            choice['price']       = format_currency(billable_choices[0]['price'], '', u'#0.00', locale='en_US') 
                            choice['quantity']    = friendly_data['nights']
                            choice['price_total'] = regdata.price
                            choice['price_info']  = billable_choices[0]['price_info']
                            choice['itemNum']     = ii
                            itemized_data.append(choice)

                elif regdata.field_data.field.input_type == 'single_choice':
                    billable_choices = [x for x in versioned_data['choices'] if x['id'] in regdata.data and x['is_billable']]
                    if billable_choices:
                        ii = ii + 1
                        choice = {}
                        choice['title']       = fieldTitle + ' - ' + unversioned_data['captions'][billable_choices[0]['id']]
                        choice['price']       = format_currency(billable_choices[0]['price'], '', u'#0.00', locale='en_US') 
                        choice['quantity']    = regdata.data[billable_choices[0]['id']]
                        choice['price_total'] = regdata.price
                        choice['price_info']  = billable_choices[0]['price_info']
                        choice['itemNum']     = ii
                        itemized_data.append(choice)
                 
                elif regdata.field_data.field.input_type == 'multi_choice':
                    billable_choices = [x for x in versioned_data['choices'] if x['id'] in regdata.data and x['is_billable']]
                    if billable_choices:
                        for bc in billable_choices:                            
                            ii = ii + 1
                            choice = {}
                            choice['title']       = fieldTitle + ' - ' + unversioned_data['captions'][bc['id']]
                            choice['price']       = format_currency(bc['price'], '', u'#0.00', locale='en_US') 
                            choice['quantity']    = regdata.data[bc['id']]
                            choice['price_total'] = bc['price'] * regdata.data[bc['id']]
                            choice['price_info']  = bc['price_info']
                            choice['itemNum']     = ii
                            itemized_data.append(choice)

                else: 
                    if regdata.price:                        
                        ii = ii + 1
                        choice = {}
                        choice['title']       = sectionTitle + ' - ' + fieldTitle
                        choice['price']       = format_currency(versioned_data['price'], '', u'#0.00', locale='en_US') 
                        if regdata.field_data.field.input_type == 'number':
                            choice['quantity'] = regdata.data
                        else:
                            choice['quantity'] = 1
                        choice['price_total'] = regdata.price
                        choice['price_info']  = versioned_data['price_info']
                        choice['itemNum']     = ii
                        itemized_data.append(choice)

        data['itemized_data'] = itemized_data
# ##################################################

        data['return_url'] = url_for_plugin('payment_paypal.success', registration.locator.uuid, _external=True)
        data['cancel_url'] = url_for_plugin('payment_paypal.cancel', registration.locator.uuid, _external=True)
        data['notify_url'] = url_for_plugin('payment_paypal.notify', registration.locator.uuid, _external=True)


