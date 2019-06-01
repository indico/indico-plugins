# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin,
                                           PaymentPluginSettingsFormBase)
from indico.util.string import remove_accents, unicode_to_ascii
from indico.web.forms.validators import UsedIf

from indico_payment_payfast import _
from indico_payment_payfast.blueprint import blueprint
from indico_payment_payfast.util import validate_business


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    url = URLField(_('API URL'), [DataRequired()], description=_('URL of the Payfast HTTP API.'))
    business = StringField(_('Business'), [Optional(), validate_business],
                           description=_('The default Payfast ID or email address associated with a Payfast account. '
                                         'Event managers will be able to override this.'))


class EventSettingsForm(PaymentEventSettingsFormBase):
    merchant_id  = StringField(_('Merchant ID'), [UsedIf(lambda form, _: form.enabled.data), DataRequired(),],
				description=_('The Payfast ID associated with a Payfast account.'))
    merchant_key = StringField(_('Merchant Key'), [UsedIf(lambda form, _: form.enabled.data), DataRequired(),],
				description=_('The Payfast key.'))
    business = StringField(_('Business'), [UsedIf(lambda form, _: form.enabled.data), DataRequired(),
                                           validate_business],
                           description=_('The Payfast ID or email address associated with a Payfast account.'))


class PayfastPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Payfast

    Provides a payment method using the Payfast IPN API.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {'method_name': 'Payfast',
                        'url': 'https://sandbox.payfast.co.za/eng/process',
                        'business': 'help@example.com'}
    # Access account via the email address on https://sandbox.payfast.co.za
    default_event_settings = {'enabled': False,
                              'method_name': None,
                              'business': None,
                              'merchant_id': '10013039',
                              'merchant_key': '2g2x3spsn6xo5',
			     }

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
        data['return_url'] = url_for_plugin('payment_payfast.success', registration.locator.uuid, _external=True)
        data['cancel_url'] = url_for_plugin('payment_payfast.cancel', registration.locator.uuid, _external=True)
        data['notify_url'] = url_for_plugin('payment_payfast.notify', registration.locator.uuid, _external=True)
