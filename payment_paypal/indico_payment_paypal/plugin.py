# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from wtforms.fields.core import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, Optional

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.payment import PaymentPluginMixin, PaymentPluginSettingsFormBase, PaymentEventSettingsFormBase
from indico.modules.payment.util import get_registrant_params
from indico.util.i18n import _
from indico.util.string import remove_accents

from indico_payment_paypal.blueprint import blueprint
from indico_payment_paypal.util import validate_business


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    url = URLField(_('API URL'), [DataRequired()], description=_('URL of the PayPal HTTP API.'))
    business = StringField(_('Business'), [Optional(), validate_business],
                           description=_('The default PayPal ID or email address associated with a PayPal account. '
                                         'Event managers will be able to override this.'))


class EventSettingsForm(PaymentEventSettingsFormBase):
    business = StringField(_('Business'), [DataRequired(), validate_business],
                           description=_('The PayPal ID or email address associated with a PayPal account.'))


class PaypalPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """PayPal

    Provides a payment method using the PayPal IPN API.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {'method_name': 'PayPal',
                        'url': 'https://www.paypal.com/cgi-bin/webscr'}

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        return blueprint

    def adjust_payment_form_data(self, data):
        event = data['event']
        registrant = data['registrant']
        params = get_registrant_params()
        data['item_name'] = '{}: registration for {}'.format(remove_accents(registrant.getFullName()),
                                                             remove_accents(event.getTitle()))
        data['return_url'] = url_for_plugin('payment_paypal.success', event, _external=True, **params)
        data['cancel_url'] = url_for_plugin('payment_paypal.cancel', event, _external=True, **params)
        data['notify_url'] = url_for_plugin('payment_paypal.notify', registrant, authkey=registrant.getRandomId(),
                                            _external=True)
