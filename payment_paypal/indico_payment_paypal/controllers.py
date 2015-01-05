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

from itertools import chain
from urllib import urlencode
from urllib2 import urlopen

import werkzeug.datastructures
from werkzeug.exceptions import BadRequest
from flask import request
from flask_pluginengine import current_plugin

from MaKaC.conference import ConferenceHolder
from MaKaC.webinterface.rh.base import RH
from indico.modules.payment.models.transactions import PaymentTransaction, TransactionAction
from indico.modules.payment.util import register_transaction
from indico.util import json

IPN_VERIFY_EXTRA_PARAMS = (('cmd', '_notify-validate'),)


class PaypalTransactionActionMapping(object):
    mapping = {'Completed': TransactionAction.complete,
               'Denied': TransactionAction.reject,
               'Pending': TransactionAction.pending}


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
        if not self._verify_business():
            return
        request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        verify_params = chain(request.form.iteritems(), IPN_VERIFY_EXTRA_PARAMS)
        verify_string = urlencode(list(verify_params))
        response = urlopen(current_plugin.settings.get('url'), data=verify_string)
        if response.read() != 'VERIFIED':
            current_plugin.logger.warning("Paypal IPN string {arg} did not validate".format(arg=verify_string))
            return
        if self._is_transaction_duplicated():
            current_plugin.logger.info("Payment not recorded because transaction was duplicated. Data received: {}"
                                       .format(request.form))
            return
        payment_status = request.form.get('payment_status')
        if payment_status == 'Failed':
            current_plugin.logger.info("Payment failed".format(payment_status))
            current_plugin.logger.info("Data received: {}".format(request.form))
            return
        if payment_status not in PaypalTransactionActionMapping.mapping.iterkeys():
            current_plugin.logger.warning("Payment status '{}' not recognized".format(payment_status))
            current_plugin.logger.warning("Data received: {}".format(request.form))
            return
        register_transaction(event_id=request.view_args['confId'],
                             registrant_id=request.args['registrantId'],
                             amount=request.form.get('mc_gross'),
                             currency=request.form.get('mc_currency'),
                             action=PaypalTransactionActionMapping.mapping[payment_status],
                             provider='paypal',
                             data=json.dumps(request.form))

    def _verify_business(self):
        return current_plugin.event_settings.get(self.event, 'business') == request.form.get('business')

    def _is_transaction_duplicated(self):
        transaction = PaymentTransaction.find_latest_for_registrant(self.registrant)
        if not transaction or transaction.provider != 'paypal':
            return False
        data = json.loads(transaction.data)
        return (data['payment_status'] == request.form.get('payment_status') and
                data['txn_id'] == request.form.get('txn_id'))
