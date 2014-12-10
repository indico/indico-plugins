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

from itertools import chain
from urllib import urlencode
from urllib2 import urlopen

import werkzeug.datastructures
from werkzeug.exceptions import BadRequest
from flask import request, jsonify
from flask_pluginengine import current_plugin

from MaKaC.conference import ConferenceHolder
from MaKaC.webinterface.rh.base import RH
from indico.core.db import db
from indico.modules.payment.models.transactions import PaymentTransaction, TransactionStatus
from indico.util import json

IPN_VERIFY_EXTRA_PARAMS = (('cmd', '_notify-validate'),)


class RHPaymentEventNotify(RH):
    """Process the notification sent by the PayPal"""

    def _checkParams(self):
        self.registrant = None
        self.event = ConferenceHolder().getById(request.view_args['confId'])
        self.registrant = self.event.getRegistrantById(request.args['registrantId'])
        if self.registrant is None:
            # TODO: which exception to raise?
            raise BadRequest
        if self.registrant.getRandomId() != request.args['authkey']:
            # TODO: which exception to raise?
            raise BadRequest

    def _process(self):
        current_plugin.logger.warning("Verifying...")
        if not self._verify_business():
            return
        request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        verify_params = chain(request.form.iteritems(), IPN_VERIFY_EXTRA_PARAMS)
        verify_string = urlencode(list(verify_params))
        response = urlopen(current_plugin.settings.get('url'), data=verify_string)
        if response.read() != 'VERIFIED':
            current_plugin.logger.warning("Paypal IPN string {arg} did not validate".format(arg=verify_string))
            return
        current_plugin.logger.warning("Transaction was verified successfully")
        # TODO: Check if the total amount has changed
        if self._is_transaction_duplicated():
            current_plugin.logger.error("Transaction was skipped because it is duplicated. Data received: {}"
                                        .format(request.form))
            return
        # Now it's OK to store the transaction
        new_transaction = PaymentTransaction(event_id=request.view_args['confId'],
                                             registrant_id=request.args['registrantId'],
                                             amount=request.form.get('mc_gross'),
                                             currency=request.form.get('mc_currency'),
                                             provider='paypal',
                                             data=json.dumps(request.form))

        # Still missing: Canceled_Reversal, Created, Expired, Pending, Processed, Voided
        if request.form.get('payment_status') == 'Completed':
            new_transaction.status = TransactionStatus.successful
        elif request.form.get('payment_status') == 'Failed':
            new_transaction.status = TransactionStatus.failed
        elif request.form.get('payment_status') == 'Denied':
            new_transaction.status = TransactionStatus.rejected  # The comment in transactions.py is confusing
        elif request.form.get('payment_status') == 'Reversed' or request.form.get('payment_status') == 'Refunded':
            new_transaction.status = TransactionStatus.cancelled
        else:
            current_plugin.logger.error("Payment status '{}' cannot be recognized"
                                        .format(request.form.get('payment_status')))
            current_plugin.logger.error("Failure in storing the transaction. Data received: {}".format(request.form))
            return
        db.session.add(new_transaction)
        db.session.flush()

        return jsonify({'status': 'complete'})

    def _verify_business(self):
        return current_plugin.event_settings.get(self.event, 'business') == request.form.get('business')

    def _is_transaction_duplicated(self):
        transaction = PaymentTransaction.find_latest_for_registrant(self.registrant)
        if not transaction:
            return False
        return (transaction.data.payment_status == request.form.get('payment_status') and
                transaction.data.txn_id == request.form.get('txn_id'))
