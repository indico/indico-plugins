# -*- coding: utf-8 -*-
##
## This file is part of the SixPay Indico EPayment Plugin.
## Copyright (C) 2017 - 2018 Max Fischer
##
## This is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## This software is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with SixPay Indico EPayment Plugin;if not, see <http://www.gnu.org/licenses/>.
"""
Callbacks for asynchronous replies by the SixPay service and to redirect the user
"""
from __future__ import unicode_literals
import urlparse
from xml.dom.minidom import parseString

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

from .utility import gettext, to_large_currency, to_small_currency

# RH from indico.web.rh
# - the logic to execute when SixPay/Users are redirected *after* a transaction
# - see blueprint.py for how RH's are mounted!


class BaseRequestHandler(RH):
    """
    Request Handler for asynchronous callbacks from SixPay

    These handlers are used either by

    - the user, when he is redirected from SixPay back to Indico
    - SixPay, when it sends back the result of a transaction
    """
    CSRF_ENABLED = False

    def _process_args(self):
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest


class TransactionFailure(Exception):
    """
    A Transaction with SixPay failed

    :param step: name of the step at which the transaction failed
    :type step: basestring
    :param details: verbose description of what went wrong
    :type step: basestring
    """
    def __init__(self, step, details=None):
        self.step = step
        self.details = details


class SixPayResponseHandler(BaseRequestHandler):
    """Handler for notification from SixPay service"""
    def __init__(self):
        super(SixPayResponseHandler, self).__init__()
        # registration context is not initialised before `self._process_args`...
        self.sixpay_url = None  # type: str

    def _process_args(self):
        super(SixPayResponseHandler, self)._process_args()
        # prefer event supplied sixpay url over global sixpay url
        self.sixpay_url = current_plugin.event_settings.get(self.registration.registration_form.event, 'url') \
            or current_plugin.settings.get('url')

    def _process(self):
        """process the reply from SixPay about the transaction"""
        try:
            self._process_confirmation()
        except TransactionFailure as err:
            current_plugin.logger.warning("SixPay transaction failed during %s: %s" % (err.step, err.details))

    def _process_confirmation(self):
        """Process the confirmation response inside indico"""
        # DATA: '<IDP
        #           MSGTYPE="PayConfirm" TOKEN="(unused)" VTVERIFY="(obsolete)" KEYID="1-0"
        #           ID="9SUO5zbOGY6OUA45b222bhvrpW2A"
        #           ACCOUNTID="401860-17795278"
        #           PROVIDERID="90"
        #           PROVIDERNAME="Saferpay Test Card"
        #           PAYMENTMETHOD="6"
        #           ORDERID="c281r4"
        #           AMOUNT="100"
        #           CURRENCY="EUR"
        #           IP="141.3.200.120"
        #           IPCOUNTRY="DE"
        #           CCCOUNTRY="US"
        #           MPI_LIABILITYSHIFT="yes"
        #           MPI_TX_CAVV="jAABBIIFmAAAAAAAAAAAAAAAAAA="
        #           MPI_XID="VVE3DQlhXR8PBD5JPzYGWW5FNgI="
        #           ECI="1"
        #           CAVV="jAABBIIFmAAAAAAAAAAAAAAAAAA="
        #           XID="VVE3DQlhXR8PBD5JPzYGWW5FNgI=" />'
        transaction_xml = request.args['DATA']
        transaction_signature = request.args['SIGNATURE']
        transaction_data = self._parse_transaction_xml(transaction_xml)
        # verify the signature of SixPay for the transaction
        # if this matches, the user completed the transaction as requested by Indico
        try:
            self._verify_signature(transaction_xml, transaction_signature, transaction_data['ID'])
            if self._is_duplicate_transaction(transaction_data=transaction_data):
                # we have already handled the transaction
                return True
            if self._confirm_transaction(transaction_data):
                self._verify_amount(transaction_data)
                self._register_transaction(transaction_data)
        except TransactionFailure as err:
            current_plugin.logger.warning("SixPay transaction failed during %s: %s" % (err.step, err.details))
            raise
        return True

    def _perform_request(self, task, endpoint, **data):
        """
        Helper for performing a request against SixPay

        :param task: description of the request, used for error handling
        :type task: basestring
        :param endpoint: the URL endpoint *relative* to the SixPay base URL
        :type endpoint: basestring
        :param **data: data passed during the request

        This will automatically raise any HTTP errors encountered during the request.
        If the request itself fails, a :py:exc:`~.TransactionFailure` is raised for ``task``.
        """
        request_url = urlparse.urljoin(self.sixpay_url, endpoint)
        response = requests.post(request_url, data)
        response.raise_for_status()
        if response.text.startswith('ERROR'):
            raise TransactionFailure(step=task, details=response.text)
        return response.text

    @staticmethod
    def _parse_transaction_xml(transaction_xml):
        """Parse the ``transaction_xml`` to a mapping"""
        mdom = parseString(transaction_xml)
        attributes = mdom.documentElement.attributes
        idp_data = {
            attributes.item(idx).name: attributes.item(idx).value
            for idx in range(attributes.length)
        }
        return idp_data

    def _verify_signature(self, transaction_xml, transaction_signature, transaction_id):
        """Verify the transaction data and signature with SixPay"""
        verification_response = self._perform_request(
            'verification', 'VerifyPayConfirm.asp',
            DATA=transaction_xml, SIGNATURE=transaction_signature
        )
        if verification_response.startswith('OK'):
            # text = 'OK:ID=56a77rg243asfhmkq3r&TOKEN=%3e235462FA23C4FE4AF65'
            content = verification_response.split(':', 1)[1]
            confirmation = dict(key_value.split('=') for key_value in content.split('&'))
            if not confirmation['ID'] == transaction_id:
                raise TransactionFailure(step='verification', details='mismatched transaction ID')
            return True
        raise RuntimeError("Expected reply 'OK:ID=...&TOKEN=...', got %r" % verification_response.text)

    def _is_duplicate_transaction(self, transaction_data):
        """Check if this transaction has already been recorded"""
        prev_transaction = self.registration.transaction
        if not prev_transaction or prev_transaction.provider != 'sixpay':
            return False
        return all(
            prev_transaction.data.get(key) == transaction_data.get(key)
            for key in ('ORDERID', 'CURRENCY', 'AMOUNT', 'ACCOUNTID')
        )

    def _verify_amount(self, transaction_data):
        """Verify the amount and currency of the payment; sends an email but still registers incorrect payments"""
        expected_amount = float(self.registration.price)
        expected_currency = self.registration.currency
        amount = float(transaction_data['AMOUNT'])
        currency = transaction_data['CURRENCY']
        if to_small_currency(expected_amount, expected_currency) == amount and expected_currency == currency:
            return True
        current_plugin.logger.warning(
            "Payment doesn't match events fee: %s %s != %s %s",
            amount, currency, to_small_currency(expected_amount, expected_currency), expected_currency
        )
        notify_amount_inconsistency(self.registration, to_large_currency(amount, currency), currency)
        return False

    def _confirm_transaction(self, transaction_data):
        """Confirm to SixPay that the transaction is accepted"""
        completion_data = {'ACCOUNTID': transaction_data['ACCOUNTID'], 'ID': transaction_data['ID']}
        if 'test.saferpay.com' in self.sixpay_url:
            # password: see "Saferpay Payment Page" specification, v5.1, section 4.6
            completion_data['spPassword'] = '8e7Yn5yk'
        completion_response = self._perform_request('confirmation', 'PayCompleteV2.asp', **completion_data)
        assert completion_response.startswith('OK')
        return True

    def _register_transaction(self, transaction_data):
        """Register the transaction persistently within Indico"""
        register_transaction(
            registration=self.registration,
            # SixPay uses SMALLEST currency, Indico expects LARGEST currency
            amount=to_large_currency(float(transaction_data['AMOUNT']), transaction_data['CURRENCY']),
            currency=transaction_data['CURRENCY'],
            action=TransactionAction.complete,
            provider='sixpay',
            data=transaction_data,
        )


class UserCancelHandler(BaseRequestHandler):
    """User Message on cancelled payment"""
    def _process(self):
        flash(gettext('You cancelled the payment.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class UserFailureHandler(BaseRequestHandler):
    """User Message on failed payment"""
    def _process(self):
        flash(gettext('Your payment has failed.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class UserSuccessHandler(SixPayResponseHandler):
    """User Message on successful payment"""
    def _process(self):
        try:
            self._process_confirmation()
        except TransactionFailure as err:
            current_plugin.logger.warning("SixPay transaction failed during %s: %s" % (err.step, err.details))
            flash(gettext('Your payment could not be confirmed. Please contact an organizer.'), 'info')
        else:
            flash(gettext('Your payment has been confirmed.'), 'success')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))
