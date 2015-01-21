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

import pytest
from flask import request
from mock import MagicMock

from indico.modules.payment.models.transactions import PaymentTransaction

from indico_payment_paypal.controllers import RHPaypalIPN
from indico_payment_paypal.plugin import PaypalPaymentPlugin


@pytest.mark.usefixtures('db', 'request_context')
@pytest.mark.parametrize(('business', 'expected'), (
    ('test', True),
    ('foo',  False)
))
def test_ipn_verify_business(business, expected):
    rh = RHPaypalIPN()
    rh.event = MagicMock(id=1)
    PaypalPaymentPlugin.event_settings.set(rh.event, 'business', 'test')
    request.form = {'business': business}
    with PaypalPaymentPlugin.instance.plugin_context():
        assert rh._verify_business() == expected


@pytest.mark.usefixtures('request_context')
@pytest.mark.parametrize(('amount', 'expected'), (
    ('13.37', True),
    ('10.00', False)
))
def test_ipn_verify_amount(mocker, amount, expected):
    nai = mocker.patch('indico_payment_paypal.controllers.notify_amount_inconsistency')
    rh = RHPaypalIPN()
    rh.event = MagicMock(id=1)
    rh.registrant = MagicMock()
    rh.registrant.getTotal.return_value = 13.37
    request.form = {'mc_gross': amount}
    with PaypalPaymentPlugin.instance.plugin_context():
        assert rh._verify_amount() == expected
        assert nai.called == (not expected)


@pytest.mark.usefixtures('request_context')
@pytest.mark.parametrize(('txn_id', 'payment_status', 'expected'), (
    ('12345',  'Completed', True),
    ('12345',  'Pending',   False),
    ('123456', 'Completed', False),
    ('123456', 'Pending',   False),
))
def test_ipn_is_transaction_duplicated(mocker, txn_id, payment_status, expected):
    flfr = mocker.patch('indico_payment_paypal.controllers.PaymentTransaction.find_latest_for_registrant')
    request.form = {'payment_status': 'Completed', 'txn_id': '12345'}
    rh = RHPaypalIPN()
    rh.registrant = MagicMock()
    flfr.return_value = None
    assert not rh._is_transaction_duplicated()
    flfr.return_value = PaymentTransaction(provider='paypal', data={'payment_status': payment_status, 'txn_id': txn_id})
    assert rh._is_transaction_duplicated() == expected


@pytest.mark.usefixtures('db', 'request_context')
@pytest.mark.parametrize('fail', (
    'business',
    'verify',
    'dup_txn',
    'fail',
    'refund',
    'negative',
    'status',
    None,
))
def test_ipn_process(mocker, fail):
    rt = mocker.patch('indico_payment_paypal.controllers.register_transaction')
    post = mocker.patch('indico_payment_paypal.controllers.requests.post')
    post.return_value.text = 'INVALID' if fail == 'verify' else 'VERIFIED'
    rh = RHPaypalIPN()
    rh._verify_business = lambda: fail != 'business'
    rh._is_transaction_duplicated = lambda: fail == 'dup_txn'
    rh.event = MagicMock(id=1)
    rh.registrant = MagicMock()
    rh.registrant.getTotal.return_value = 10.00
    payment_status = {'fail': 'Failed', 'refund': 'Refunded', 'status': 'Foobar'}.get(fail, 'Completed')
    amount = '-10.00' if fail == 'negative' else '10.00'
    request.view_args = {'confId': rh.event.id}
    request.args = {'registrantId': '1'}
    request.form = {'payment_status': payment_status, 'txn_id': '12345', 'mc_gross': amount,
                    'mc_currency': 'EUR'}
    with PaypalPaymentPlugin.instance.plugin_context():
        rh._process()
        assert post.called == (fail != 'business')
        assert rt.called == (fail is None)
