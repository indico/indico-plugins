# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from itertools import chain

import requests
from flask import flash, redirect, request
from flask_pluginengine import current_plugin
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.notifications import notify_amount_inconsistency
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from indico_payment_paypal import _


IPN_VERIFY_EXTRA_PARAMS = (('cmd', '_notify-validate'),)


paypal_transaction_action_mapping = {'Completed': TransactionAction.complete,
                                     'Denied': TransactionAction.reject,
                                     'Pending': TransactionAction.pending}


class RHPaypalIPN(RH):
    """Process the notification sent by the PayPal"""

    CSRF_ENABLED = False

    def _process_args(self):
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest

    def _process(self):
        self._verify_business()
        verify_params = list(chain(IPN_VERIFY_EXTRA_PARAMS, request.form.iteritems()))
        result = requests.post(current_plugin.settings.get('url'), data=verify_params).text
        if result != 'VERIFIED':
            current_plugin.logger.warning("Paypal IPN string %s did not validate (%s)", verify_params, result)
            return
        if self._is_transaction_duplicated():
            current_plugin.logger.info("Payment not recorded because transaction was duplicated\nData received: %s",
                                       request.form)
            return
        payment_status = request.form.get('payment_status')
        if payment_status == 'Failed':
            current_plugin.logger.info("Payment failed (status: %s)\nData received: %s", payment_status, request.form)
            return
        if payment_status == 'Refunded' or float(request.form.get('mc_gross')) <= 0:
            current_plugin.logger.warning("Payment refunded (status: %s)\nData received: %s",
                                          payment_status, request.form)
            return
        if payment_status not in paypal_transaction_action_mapping:
            current_plugin.logger.warning("Payment status '%s' not recognized\nData received: %s",
                                          payment_status, request.form)
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
        candidates = {request.form.get('business'),
                      request.form.get('receiver_id'),
                      request.form.get('receiver_email')}
        if expected in candidates:
            return True
        current_plugin.logger.warning("Unexpected business: %s not in %r (request data: %r)", expected, candidates,
                                      request.form)
        return False

    def _verify_amount(self):
        expected_amount = self.registration.price
        expected_currency = self.registration.currency
        amount = float(request.form['mc_gross'])
        currency = request.form['mc_currency']
        if expected_amount == amount and expected_currency == currency:
            return True
        current_plugin.logger.warning("Payment doesn't match event's fee: %s %s != %s %s",
                                      amount, currency, expected_amount, expected_currency)
        notify_amount_inconsistency(self.registration, amount, currency)
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
