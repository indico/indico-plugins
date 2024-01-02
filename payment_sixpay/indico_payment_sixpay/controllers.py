# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2024 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import json
import time
from urllib.parse import urljoin

import requests
from flask import flash, redirect, request
from requests import RequestException
from werkzeug.exceptions import BadRequest, NotFound

from indico.core.plugins import url_for_plugin
from indico.modules.events.payment.controllers import RHPaymentBase
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.notifications import notify_amount_inconsistency
from indico.modules.events.payment.util import TransactionStatus, get_active_payment_plugins, register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from indico_payment_sixpay import _
from indico_payment_sixpay.plugin import SixpayPaymentPlugin
from indico_payment_sixpay.util import (PROVIDER_SIXPAY, SIXPAY_JSON_API_SPEC, SIXPAY_PP_ASSERT_URL,
                                        SIXPAY_PP_CANCEL_URL, SIXPAY_PP_CAPTURE_URL, SIXPAY_PP_INIT_URL,
                                        get_request_header, get_terminal_id, to_large_currency, to_small_currency)


class TransactionFailure(Exception):
    """A transaction with SIXPay failed.

    :param step: name of the step at which the transaction failed
    :param details: verbose description of what went wrong
    """

    def __init__(self, step, details=None):
        self.step = step
        self.details = details


class RHSixpayBase(RH):
    """Request Handler for asynchronous callbacks from SIXPay.

    These handlers are used either by

    - the user, when he is redirected from SIXPay back to Indico
    - SIXPay, when it sends back the result of a transaction
    """

    CSRF_ENABLED = False

    def _process_args(self):
        self.registration = Registration.query.filter_by(uuid=request.args['token']).first()
        if not self.registration:
            raise BadRequest
        try:
            self.token = self.registration.transaction.data['Init_PP_response']['Token']
        except KeyError:
            # if the transaction was already recorded as successful via background notification,
            # we no longer have a token in the local transaction
            self.token = None


class RHInitSixpayPayment(RHPaymentBase):
    def _get_transaction_parameters(self):
        """Get parameters for creating a transaction request."""
        settings = SixpayPaymentPlugin.event_settings.get_all(self.event)
        format_map = {
            'user_id': self.registration.user_id,
            'user_name': self.registration.full_name,
            'user_firstname': self.registration.first_name,
            'user_lastname': self.registration.last_name,
            'event_id': self.registration.event_id,
            'event_title': self.registration.event.title,
            'registration_id': self.registration.id,
            'regform_title': self.registration.registration_form.title
        }
        order_description = settings['order_description'].format(**format_map)
        order_identifier = settings['order_identifier'].format(**format_map)
        # see the SIXPay Manual
        # https://saferpay.github.io/jsonapi/#Payment_v1_PaymentPage_Initialize
        # on what these things mean
        transaction_parameters = {
            'RequestHeader': get_request_header(SIXPAY_JSON_API_SPEC, settings['account_id']),
            'TerminalId': get_terminal_id(settings['account_id']),
            'Payment': {
                'Amount': {
                    # indico handles price as largest currency, but six expects
                    # smallest. E.g. EUR: indico uses 100.2 Euro, but six
                    # expects 10020 Cent
                    'Value': str(to_small_currency(self.registration.price, self.registration.currency)),
                    'CurrencyCode': self.registration.currency,
                },
                'OrderId': order_identifier[:80],
                'DESCRIPTION': order_description[:1000],
            },
            # callbacks of the transaction - where to announce success etc., when redircting the user
            'ReturnUrls': {
                'Success': url_for_plugin('payment_sixpay.success', self.registration.locator.uuid, _external=True),
                'Fail': url_for_plugin('payment_sixpay.failure', self.registration.locator.uuid, _external=True),
                'Abort': url_for_plugin('payment_sixpay.cancel', self.registration.locator.uuid, _external=True)
            },
            'Notification': {
                # where to asynchronously call back from SIXPay
                'NotifyUrl': url_for_plugin('payment_sixpay.notify', self.registration.locator.uuid, _external=True)
            }
        }
        if settings['notification_mail']:
            transaction_parameters['Notification']['MerchantEmails'] = [settings['notification_mail']]
        return transaction_parameters

    def _init_payment_page(self, transaction_data):
        """Initialize payment page."""
        endpoint = urljoin(SixpayPaymentPlugin.settings.get('url'), SIXPAY_PP_INIT_URL)
        credentials = (SixpayPaymentPlugin.settings.get('username'), SixpayPaymentPlugin.settings.get('password'))
        resp = requests.post(endpoint, json=transaction_data, auth=credentials)
        try:
            resp.raise_for_status()
        except RequestException as exc:
            SixpayPaymentPlugin.logger.error('Could not initialize payment: %s', exc.response.text)
            raise Exception('Could not initialize payment')
        return resp.json()

    def _process_args(self):
        RHPaymentBase._process_args(self)
        if 'sixpay' not in get_active_payment_plugins(self.event):
            raise NotFound
        if not SixpayPaymentPlugin.instance.supports_currency(self.registration.currency):
            raise BadRequest

    def _process(self):
        transaction_params = self._get_transaction_parameters()
        init_response = self._init_payment_page(transaction_params)
        payment_url = init_response['RedirectUrl']

        # create pending transaction and store Saferpay transaction token
        new_indico_txn = register_transaction(
            self.registration,
            self.registration.price,
            self.registration.currency,
            TransactionAction.pending,
            PROVIDER_SIXPAY,
            {'Init_PP_response': init_response}
        )
        if not new_indico_txn:
            # set it on the current transaction if we could not create a next one
            # this happens if we already have a pending transaction and it's incredibly
            # ugly...
            self.registration.transaction.data = {'Init_PP_response': init_response}
        return redirect(payment_url)


class SixpayNotificationHandler(RHSixpayBase):
    """Handler for notification from SIXPay service."""

    def _process(self):
        """Process the reply from SIXPay about the transaction."""
        if self.token is not None:
            self._process_confirmation()

    def _process_confirmation(self):
        """Process the confirmation response inside indico."""
        # assert transaction status from SIXPay
        try:
            assert_response = self._assert_payment()
            if self._is_duplicate_transaction(assert_response):
                # we have already handled the transaction
                return
            elif self._is_captured(assert_response):
                # We already captured the payment. This usually happens because sixpay
                # calls a background notification endpoint but we also try to capture
                # it after being redirected to the user-facing success endpoint
                SixpayPaymentPlugin.logger.info('Not processing already-captured transaction')
                time.sleep(1)  # wait a bit to make sure the other request finished!
                return
            elif self._is_authorized(assert_response):
                self._capture_transaction(assert_response)
                self._verify_amount(assert_response)
                self._register_payment(assert_response)
        except TransactionFailure as exc:
            if exc.step == 'capture':
                try:
                    payload = json.loads(exc.details)
                except (json.JSONDecodeError, TypeError):
                    payload = {}
                if payload.get('ErrorName') == 'TRANSACTION_ALREADY_CAPTURED':
                    # Same as the self._is_captured(assert_response) case above, but a race
                    # between the two requests (user-facing and background) resulted in both
                    # asserts returning an 'authorized' state
                    SixpayPaymentPlugin.logger.info('Not processing already-captured transaction (parallel request)')
                    time.sleep(1)  # wait a bit to make sure the other request finished
                    return
            SixpayPaymentPlugin.logger.warning('SIXPay transaction failed during %s: %s', exc.step, exc.details)
            raise

    def _perform_request(self, task, endpoint, data):
        """Perform a request against SIXPay.

        :param task: description of the request, used for error handling
        :param endpoint: the URL endpoint *relative* to the SIXPay base URL
        :param **data: data passed during the request

        This will automatically raise any HTTP errors encountered during the
        request. If the request itself fails, a :py:exc:`~.TransactionFailure`
        is raised for ``task``.
        """
        request_url = urljoin(SixpayPaymentPlugin.settings.get('url'), endpoint)
        credentials = (SixpayPaymentPlugin.settings.get('username'), SixpayPaymentPlugin.settings.get('password'))
        response = requests.post(request_url, json=data, auth=credentials)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise TransactionFailure(step=task, details=response.text)
        return response

    def _assert_payment(self):
        """Check the status of the transaction with SIXPay.

        Returns transaction assert data.
        """
        account_id = SixpayPaymentPlugin.event_settings.get(self.registration.event, 'account_id')
        assert_response = self._perform_request(
            'assert',
            SIXPAY_PP_ASSERT_URL,
            {
                'RequestHeader': get_request_header(SIXPAY_JSON_API_SPEC, account_id),
                'Token': self.token,
            }
        )
        if assert_response.ok:
            return assert_response.json()

    def _is_duplicate_transaction(self, transaction_data):
        """Check if this transaction has already been recorded."""
        prev_transaction = self.registration.transaction
        if (
            not prev_transaction or
            prev_transaction.provider != PROVIDER_SIXPAY or
            'Transaction' not in prev_transaction.data
        ):
            return False
        old = prev_transaction.data['Transaction']
        new = transaction_data['Transaction']
        return (
            old['OrderId'] == new['OrderId'] and
            old['Type'] == new['Type'] and
            old['Id'] == new['Id'] and
            old['SixTransactionReference'] == new['SixTransactionReference'] and
            old['Amount']['Value'] == new['Amount']['Value'] and
            old['Amount']['CurrencyCode'] == new['Amount']['CurrencyCode']
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
        if to_small_currency(expected_amount, expected_currency) == amount and expected_currency == currency:
            return True
        SixpayPaymentPlugin.logger.warning("Payment doesn't match event's fee: %s %s != %s %s",
                                           amount, currency, to_small_currency(expected_amount, expected_currency),
                                           expected_currency)
        notify_amount_inconsistency(self.registration, to_large_currency(amount, currency), currency)
        return False

    def _capture_transaction(self, assert_data):
        """Confirm to SIXPay that the transaction is accepted.

        On success returns the response JSON data.
        """
        account_id = SixpayPaymentPlugin.event_settings.get(self.registration.event, 'account_id')
        capture_data = {
            'RequestHeader': get_request_header(SIXPAY_JSON_API_SPEC, account_id),
            'TransactionReference': {'TransactionId': assert_data['Transaction']['Id']}
        }
        capture_response = self._perform_request('capture', SIXPAY_PP_CAPTURE_URL, capture_data)
        return capture_response.json()

    def _cancel_transaction(self, assert_data):
        """Inform Sixpay that the transaction is canceled.

        Cancel the transaction at Sixpay. This method is implemented but
        not used and tested yet.
        """
        account_id = SixpayPaymentPlugin.event_settings.get(self.registration.event, 'account_id')
        cancel_data = {
            'RequestHeader': get_request_header(
                SIXPAY_JSON_API_SPEC, account_id
            ),
            'TransactionReference': {
                'TransactionId': assert_data['Transaction']['Id']
            }
        }
        cancel_response = self._perform_request(
            'cancel', SIXPAY_PP_CANCEL_URL, cancel_data
        )
        return cancel_response.json()

    def _register_payment(self, assert_data):
        """Register the transaction as paid."""
        register_transaction(
            self.registration,
            self.registration.transaction.amount,
            self.registration.transaction.currency,
            TransactionAction.complete,
            PROVIDER_SIXPAY,
            data={'Transaction': assert_data['Transaction']}
        )


class UserCancelHandler(RHSixpayBase):
    """User redirect target in case of cancelled payment."""

    def _process(self):
        register_transaction(
            self.registration,
            self.registration.transaction.amount,
            self.registration.transaction.currency,
            # XXX: this is indeed reject and not cancel (cancel is "mark as unpaid" and
            # only used for manual transactions)
            TransactionAction.reject,
            provider=PROVIDER_SIXPAY,
        )
        flash(_('You cancelled the payment.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class UserFailureHandler(RHSixpayBase):
    """User redirect target in case of failed payment."""

    def _process(self):
        register_transaction(
            self.registration,
            self.registration.transaction.amount,
            self.registration.transaction.currency,
            TransactionAction.reject,
            provider=PROVIDER_SIXPAY,
        )
        flash(_('Your payment has failed.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class UserSuccessHandler(SixpayNotificationHandler):
    """User redirect target in case of successful payment."""

    def _process(self):
        try:
            if self.token is not None:
                self._process_confirmation()
        except TransactionFailure:
            flash(_('Your payment could not be confirmed. Please contact the event organizers.'), 'warning')
        else:
            if self.registration.transaction.status == TransactionStatus.successful:
                flash(_('Your payment has been confirmed.'), 'success')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))
