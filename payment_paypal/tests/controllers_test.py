# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest
from flask import request
from mock import MagicMock

from indico.modules.events.payment.models.transactions import PaymentTransaction

from indico_payment_paypal.controllers import RHPaypalIPN
from indico_payment_paypal.plugin import PaypalPaymentPlugin


@pytest.mark.usefixtures('db', 'request_context')
@pytest.mark.parametrize(('formdata', 'expected'), (
    ({'business': 'test'},       True),
    ({'receiver_id': 'test'},    True),
    ({'receiver_email': 'test'}, True),
    ({'business': 'foo'},        False),
    ({},                         False)
))
def test_ipn_verify_business(formdata, expected, dummy_event):
    rh = RHPaypalIPN()
    rh.registration = MagicMock()
    rh.registration.registration_form.event = dummy_event
    PaypalPaymentPlugin.event_settings.set(dummy_event, 'business', 'test')
    request.form = formdata
    with PaypalPaymentPlugin.instance.plugin_context():
        assert rh._verify_business() == expected


@pytest.mark.usefixtures('request_context')
@pytest.mark.parametrize(('amount', 'currency', 'expected'), (
    ('13.37', 'EUR', True),
    ('13.37', 'CHF', False),
    ('10.00', 'CHF', False),
    ('10.00', 'CHF', False),
))
def test_ipn_verify_amount(mocker, amount, currency, expected):
    nai = mocker.patch('indico_payment_paypal.controllers.notify_amount_inconsistency')
    rh = RHPaypalIPN()
    rh.event = MagicMock(id=1)
    rh.registration = MagicMock()
    rh.registration.price = 13.37
    rh.registration.currency = currency
    request.form = {'mc_gross': amount, 'mc_currency': 'EUR'}
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
def test_ipn_is_transaction_duplicated(txn_id, payment_status, expected):
    request.form = {'payment_status': 'Completed', 'txn_id': '12345'}
    rh = RHPaypalIPN()
    rh.registration = MagicMock()
    rh.registration.transaction = None
    assert not rh._is_transaction_duplicated()
    transaction = PaymentTransaction(provider='paypal', data={'payment_status': payment_status, 'txn_id': txn_id})
    rh.registration.transaction = transaction
    assert rh._is_transaction_duplicated() == expected


@pytest.mark.usefixtures('db', 'request_context')
@pytest.mark.parametrize('fail', (
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
    mocker.patch('indico_payment_paypal.controllers.notify_amount_inconsistency')
    post.return_value.text = 'INVALID' if fail == 'verify' else 'VERIFIED'
    rh = RHPaypalIPN()
    rh._is_transaction_duplicated = lambda: fail == 'dup_txn'
    rh.event = MagicMock(id=1)
    rh.registration = MagicMock()
    rh.registration.getTotal.return_value = 10.00
    payment_status = {'fail': 'Failed', 'refund': 'Refunded', 'status': 'Foobar'}.get(fail, 'Completed')
    amount = '-10.00' if fail == 'negative' else '10.00'
    request.view_args = {'confId': rh.event.id}
    request.args = {'registrantId': '1'}
    request.form = {'payment_status': payment_status, 'txn_id': '12345', 'mc_gross': amount,
                    'mc_currency': 'EUR', 'business': 'foo@bar.com'}
    with PaypalPaymentPlugin.instance.plugin_context():
        rh._process()
        assert post.called
        assert rt.called == (fail is None)
