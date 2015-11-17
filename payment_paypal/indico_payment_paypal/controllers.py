# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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

from itertools import chain

import requests
from flask import request, flash, redirect
from flask_pluginengine import current_plugin
from werkzeug.exceptions import BadRequest

from indico.modules.events.registration.models.registrations import Registration
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.notifications import notify_amount_inconsistency
from indico.modules.events.payment.util import register_transaction
from indico.web.flask.util import url_for
from MaKaC.webinterface.rh.base import RH

from indico_payment_paypal import _


IPN_VERIFY_EXTRA_PARAMS = (('cmd', '_notify-validate'),)


paypal_transaction_action_mapping = {'Completed': TransactionAction.complete,
                                     'Denied': TransactionAction.reject,
                                     'Pending': TransactionAction.pending}


class RHPaypalIPN(RH):
    """Process the notification sent by the PayPal"""

    def _checkParams(self):
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest

    def _process(self):
        self._verify_business()
        verify_params = list(chain(IPN_VERIFY_EXTRA_PARAMS, request.form.iteritems()))
        result = requests.post(current_plugin.settings.get('url'), data=verify_params).text
        if result != 'VERIFIED':
            current_plugin.logger.warning("Paypal IPN string {} did not validate ({})".format(verify_params, result))
            return
        if self._is_transaction_duplicated():
            current_plugin.logger.info("Payment not recorded because transaction was duplicated\n"
                                       "Data received: {}".format(request.form))
            return
        payment_status = request.form.get('payment_status')
        if payment_status == 'Failed':
            current_plugin.logger.info("Payment failed (status: {})\n"
                                       "Data received: {}".format(payment_status, request.form))
            return
        if payment_status == 'Refunded' or float(request.form.get('mc_gross')) <= 0:
            current_plugin.logger.warning("Payment refunded (status: {})\n"
                                          "Data received: {}".format(payment_status, request.form))
            return
        if payment_status not in paypal_transaction_action_mapping:
            current_plugin.logger.warning("Payment status '{}' not recognized\n"
                                          "Data received: {}".format(payment_status, request.form))
            return
        self._verify_amount()
        register_transaction(registration=self.registration,
                             amount=float(request.form['mc_gross']),
                             currency=request.form['mc_currency'],
                             action=paypal_transaction_action_mapping[payment_status],
                             provider='paypal',
                             data=request.form)

    def _verify_business(self):
        expected = current_plugin.event_settings.get(self.registration.registration_form.event, 'business')
        business = request.form.get('business')
        if expected == business:
            return True
        current_plugin.logger.warning("Unexpected business: {} != {}".format(business, expected))
        current_plugin.logger.warning("Request data was: {}".format(request.form))
        return False

    def _verify_amount(self):
        expected = self.registration.price
        amount = float(request.form['mc_gross'])
        if expected == amount:
            return True
        current_plugin.logger.warning("Paid amount doesn't match event's fee: {} != {}".format(amount, expected))
        notify_amount_inconsistency(self.registration, amount)
        return False

    def _is_transaction_duplicated(self):
        transaction = self.registration.transaction
        if not transaction or transaction.provider != 'paypal':
            return False
        return (transaction.data['payment_status'] == request.form.get('payment_status') and
                transaction.data['txn_id'] == request.form.get('txn_id'))


class RHPaypalSuccess(RHPaypalIPN):
    """Confirmation message after successful payment"""

    def _process(self):
        flash(_('Your payment request has been processed.'), 'success')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class RHPaypalCancel(RHPaypalIPN):
    """Cancellation message"""

    def _process(self):
        flash(_('You cancelled the payment process.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))
