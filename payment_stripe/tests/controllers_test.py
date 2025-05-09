# This file is part of the Indico plugins.
# Copyright (C) 2019 - 2025 <original contributors tbd>, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from flask import request

from indico.modules.events.payment.models.transactions import TransactionAction

from indico_payment_stripe.controllers import RHStripeSuccess
from indico_payment_stripe.plugin import StripePaymentPlugin
from indico_payment_stripe.util import conv_from_stripe_amount, conv_to_stripe_amount


pytest_plugins = ('indico.modules.events.registration.testing.fixtures',)


@pytest.mark.parametrize(('curr', 'indico_amount', 'stripe_amount'), (
    # Currency with decimals
    ('EUR', Decimal('10.01'), 1001),
    # Currenty without decimals
    ('JPY', Decimal(3690), 3690),
    # Currency with more than 2 decimals
    ('JOD', Decimal('12.345'), 12345),
))
def test_conv_amounts(curr, indico_amount, stripe_amount):
    assert conv_to_stripe_amount(indico_amount, curr) == stripe_amount
    assert conv_from_stripe_amount(stripe_amount, curr) == indico_amount


@pytest.mark.parametrize('use_event_keys', (True, False))
@pytest.mark.usefixtures('request_context')
def test_handler_process(mocker, dummy_event, dummy_regform, dummy_reg, use_event_keys):
    StripePaymentPlugin.settings.set('sec_key', 'secret-global')
    StripePaymentPlugin.event_settings.set(dummy_event, 'use_event_api_keys', use_event_keys)
    StripePaymentPlugin.event_settings.set(dummy_event, 'sec_key', 'secret-event')
    expected_api_key = ('secret-event' if use_event_keys else 'secret-global')

    dummy_reg.currency = 'EUR'
    dummy_reg.base_price = Decimal('13.37')

    rt = mocker.patch('indico_payment_stripe.controllers.register_transaction')
    stripe = mocker.patch('indico_payment_stripe.controllers.stripe')
    stripe_session = stripe.checkout.Session.retrieve
    stripe_payment_intent = stripe.PaymentIntent.retrieve

    stripe_response = {
        'id': 1,
        'status': 'succeeded',
        'amount': conv_to_stripe_amount(dummy_reg.price, dummy_reg.currency),
        'currency': dummy_reg.currency.lower(),
        'client_secret': 'secret',
    }

    stripe.PaymentIntent.retrieve.return_value = stripe_response
    session_id = 'cs_test_foobar'

    request.view_args = {'event_id': dummy_event.id, 'reg_form_id': dummy_regform.id}
    request.args = {'token': dummy_reg.uuid, 'session_id': session_id}

    rh = RHStripeSuccess()
    with StripePaymentPlugin.instance.plugin_context():
        rh._process_args()

    assert rh.stripe_api_key == expected_api_key
    stripe_session.assert_called_once_with(
        session_id,
        api_key=expected_api_key,
    )

    payment_intent_id = 'pi_test'
    rh.session = MagicMock(payment_intent=payment_intent_id)
    with StripePaymentPlugin.instance.plugin_context():
        rh._process()

    stripe_payment_intent.assert_called_once_with(
        payment_intent_id,
        api_key=expected_api_key,
    )

    del stripe_response['client_secret']  # this one must NOT be in the recorded data
    rt.assert_called_once_with(
        registration=rh.registration,
        amount=dummy_reg.price,
        currency=dummy_reg.currency,
        action=TransactionAction.complete,
        provider='stripe',
        data=stripe_response,
    )
