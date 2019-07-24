# -*- coding: utf-8 -*-
#
# This file is part of the SixPay Indico EPayment Plugin.
# Copyright (C) 2017 - 2018 Max Fischer
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SixPay Indico EPayment Plugin;
# if not, see <http://www.gnu.org/licenses/>.
"""Callbacks for asynchronous replies by Saferpay and to redirect the user."""
from __future__ import unicode_literals
import urlparse

import requests
from flask import flash, redirect, request
from flask_pluginengine import current_plugin
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.notifications \
    import notify_amount_inconsistency
from indico.modules.events.registration.models.registrations \
    import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from .utility import (
    gettext, to_large_currency, to_small_currency, get_request_header,
    get_setting
)
from .utility import (
    saferpay_pp_assert_url,
    saferpay_pp_capture_url,
    saferpay_json_api_spec,
    saferpay_pp_cancel_url,
    provider
)

# RH from indico.web.rh
# - the logic to execute when SixPay/Users are redirected *after* a transaction
# - see blueprint.py for how RH's are mounted!


class BaseRequestHandler(RH):
    """Request Handler for asynchronous callbacks from SixPay.

    These handlers are used either by

    - the user, when he is redirected from SixPay back to Indico
    - SixPay, when it sends back the result of a transaction
    """

    CSRF_ENABLED = False

    def _process_args(self):
        self.registration = Registration.find_first(uuid=request.args['token'])
        if not self.registration:
            raise BadRequest
        self.token = (
            self.registration.transaction.data['Init_PP_response']['Token']
        )

    def _get_setting(self, setting):
        return get_setting(setting, self.registration.registration_form.event)


class TransactionFailure(Exception):
    """A Transaction with SixPay failed.

    :param step: name of the step at which the transaction failed
    :type step: basestring
    :param details: verbose description of what went wrong
    :type step: basestring
    """

    def __init__(self, step, details=None):
        """Initialize request handler."""
        self.step = step
        self.details = details


class SixPayResponseHandler(BaseRequestHandler):
    """Handler for notification from SixPay service."""

    def __init__(self):
        """Initialize request handler."""
        super(SixPayResponseHandler, self).__init__()
        # registration context is not initialised before `self._process_args`
        self.sixpay_url = None  # type: str

    def _process_args(self):
        super(SixPayResponseHandler, self)._process_args()
        self.sixpay_url = get_setting('url')

    def _process(self):
        """Process the reply from SixPay about the transaction."""
        try:
            self._process_confirmation()
        except TransactionFailure as err:
            current_plugin.logger.warning(
                "SixPay transaction failed during %s: %s"
                % (err.step, err.details)
            )

    def _process_confirmation(self):
        """Process the confirmation response inside indico."""
        transaction_data = request.json
        # transaction_signature = request.args['SIGNATURE']
        # transaction_data = self._parse_transaction_xml(transaction_xml)
        # assert transaction status from SixPay
        try:
            assert_response = self._assert_payment(transaction_data)
            if self._is_duplicate_transaction(assert_response):
                # we have already handled the transaction
                return True
            if (
                self._is_authorized(assert_response)
                and not self._is_captured(assert_response)
            ):
                capture_response = self._capture_transaction(assert_response)
                assert_response['CaptureResponse'] = capture_response
                self._verify_amount(assert_response)
                self._register_payment(assert_response)
        except TransactionFailure as err:
            current_plugin.logger.warning(
                "SixPay transaction failed during %s: %s"
                % (err.step, err.details)
            )
            raise
        return True

    def _perform_request(self, task, endpoint, data):
        """Perform a request against SixPay.

        :param task: description of the request, used for error handling
        :type task: basestring
        :param endpoint: the URL endpoint *relative* to the SixPay base URL
        :type endpoint: basestring
        :param **data: data passed during the request

        This will automatically raise any HTTP errors encountered during the
        request. If the request itself fails, a :py:exc:`~.TransactionFailure`
        is raised for ``task``.
        """
        request_url = urlparse.urljoin(self.sixpay_url, endpoint)
        credentials = (
            get_setting('username'),
            get_setting('password')
        )
        response = requests.post(
            request_url, json=data, auth=credentials
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise TransactionFailure(
                step=task,
                details=response.text
            )
        return response

    def _assert_payment(self, transaction_data):
        """Check the status of the transaction with SixPay.

        Returns transaction assert data.
        """
        assert_response = self._perform_request(
            'assert',
            saferpay_pp_assert_url,
            {
                'RequestHeader': get_request_header(
                    saferpay_json_api_spec, self._get_setting('account_id')
                ),
                'Token': self.token,
            }
        )
        if assert_response.status_code == requests.codes.ok:
            return assert_response.json()

    def _is_duplicate_transaction(self, transaction_data):
        """Check if this transaction has already been recorded."""
        prev_transaction = self.registration.transaction
        if (
            not prev_transaction
            or prev_transaction.provider != 'sixpay'
            or 'Transaction' not in prev_transaction.data
        ):
            return False
        old = prev_transaction.data.get('Transaction')
        new = transaction_data.get('Transaction')
        return (
            old['OrderId'] == new['OrderId']
            & old['Type'] == new['Type']
            & old['Id'] == new['Id']
            & old['SixTransactionReference'] == new['SixTransactionReference']
            & old['Amount']['Value'] == new['Amount']['Value']
            & old['Amount']['CurrencyCode'] == new['Amount']['CurrencyCode']
        )

    def _is_authorized(self, assert_data):
        """Check if payment is authorized."""
        return assert_data['Transaction']['Status'] == 'AUTHORIZED'

    def _is_captured(self, assert_data):
        """Check if payment is captured, i.e. the cash flow is triggered."""
        return assert_data['Transaction']['Status'] == 'CAPTURED'

    def _verify_amount(self, assert_data):
        """Verify the amount and currency of the payment.

        Sends an email but still registers incorrect payments.
        """
        expected_amount = float(self.registration.price)
        expected_currency = self.registration.currency
        amount = float(assert_data['Transaction']['Amount']['Value'])
        currency = assert_data['Transaction']['Amount']['CurrencyCode']
        if (
            to_small_currency(expected_amount, expected_currency) == amount
            and expected_currency == currency
        ):
            return True
        current_plugin.logger.warning(
            "Payment doesn't match events fee: %s %s != %s %s",
            amount, currency,
            to_small_currency(expected_amount, expected_currency),
            expected_currency
        )
        notify_amount_inconsistency(
            self.registration,
            to_large_currency(amount, currency),
            currency
        )
        return False

    def _capture_transaction(self, assert_data):
        """Confirm to SixPay that the transaction is accepted.

        On success returns the response JSON data.
        """
        capture_data = {
            'RequestHeader': get_request_header(
                saferpay_json_api_spec, self._get_setting('account_id')
            ),
            'TransactionReference': {
                'TransactionId': assert_data['Transaction']['Id']
            }
        }
        capture_response = self._perform_request(
            'capture', saferpay_pp_capture_url, capture_data
        )
        return capture_response.json()

    def _cancel_transaction(self, assert_data):
        """Inform Sixpay that the transaction is canceled.

        Cancel the transaction at Sixpay. This method is implemented but
        not used and tested yet.
        """
        cancel_data = {
            'RequestHeader': get_request_header(
                saferpay_json_api_spec, self._get_setting('account_id')
            ),
            'TransactionReference': {
                'TransactionId': assert_data['Transaction']['Id']
            }
        }
        cancel_response = self._perform_request(
            'cancel', saferpay_pp_cancel_url, cancel_data
        )
        return cancel_response.json()

    def _register_payment(self, assert_data):
        """Register the transaction as paid."""
        self.registration.transaction.create_next(
            registration=self.registration,
            amount=self.registration.transaction.amount,
            currency=self.registration.transaction.currency,
            action=TransactionAction.complete,
            provider=provider
        )
        self.registration.update_state(paid=True)


class UserCancelHandler(BaseRequestHandler):
    """User Message on cancelled payment."""

    def _process(self):
        self.registration.transaction.create_next(
            registration=self.registration,
            amount=self.registration.transaction.amount,
            currency=self.registration.transaction.currency,
            action=TransactionAction.reject,
            provider=provider
        )
        flash(gettext('You cancelled the payment.'), 'info')
        return redirect(url_for(
            'event_registration.display_regform',
            self.registration.locator.registrant)
        )


class UserFailureHandler(BaseRequestHandler):
    """User Message on failed payment."""

    def _process(self):
        self.registration.transaction.create_next(
            registration=self.registration,
            amount=self.registration.transaction.amount,
            currency=self.registration.transaction.currency,
            action=TransactionAction.reject,
            provider=provider
        )
        flash(gettext('Your payment has failed.'), 'info')
        return redirect(url_for(
            'event_registration.display_regform',
            self.registration.locator.registrant)
        )


class UserSuccessHandler(SixPayResponseHandler):
    """User Message on successful payment."""

    def _process(self):
        try:
            self._process_confirmation()
        except TransactionFailure as err:
            current_plugin.logger.warning(
                "SixPay transaction failed during %s: %s" % (
                    err.step, err.details
                )
            )
            flash(gettext(
                'Your payment could not be confirmed.'
                ' Please contact an organizer.'),
                'info'
            )
        else:
            flash(gettext('Your payment has been confirmed.'), 'success')
        return redirect(url_for(
            'event_registration.display_regform',
            self.registration.locator.registrant)
        )
