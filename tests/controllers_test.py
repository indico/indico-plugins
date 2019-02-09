# -*- coding: utf-8 -*-
"""
    controllers tests
    ~~~~~~~~~~~~~~~~~

"""

import pytest
from flask import request
from mock import MagicMock

from indico.modules.events.payment.models.transactions import TransactionAction
from indico_payment_stripe.controllers import RHStripe
from indico_payment_stripe.plugin import StripePaymentPlugin


@pytest.mark.parametrize('curr, indico_amount, stripe_amount', [
    ('EUR', 10.01, 1001),
    ('JPY', 3690, 3690),
])
def test_handler_process(
    curr, indico_amount, stripe_amount,
    mocker, db, dummy_event, request_context,
):

    StripePaymentPlugin.event_settings.set(
        dummy_event,
        'use_event_api_keys',
        True,
    )
    StripePaymentPlugin.event_settings.set(
        dummy_event,
        'sec_key',
        'mock_sec_key'
    )
    StripePaymentPlugin.event_settings.set(
        dummy_event,
        'description',
        'mock_description'
    )

    rt = mocker.patch('indico_payment_stripe.controllers.register_transaction')
    stripe = mocker.patch('indico_payment_stripe.controllers.stripe')
    stripe_charge = stripe.Charge.create
    # This is a pared down return value of the API call, where we only define
    # the attributes actually used afterwards.
    stripe.Charge.create.return_value = {
        'status': 'succeeded',
        'amount': stripe_amount,
        'currency': curr,
        'outcome': {
            'type': 'authorized'
        },
        'receipt_url': 'https://foo.com'
    }

    rh = RHStripe()
    rh.event = MagicMock(id=1)
    rh.registration = MagicMock(registration_form_id=3)
    rh.registration.registration_form.event = dummy_event
    rh.registration.price = indico_amount
    rh.registration.currency = curr
    rh.registration.registration_form.event.sec_key = 'foo'
    rh.registration.registration_form.event.description = 'bar'
    rh.registration.locator.registrant = {
        'confId': rh.event.id,
        'reg_form_id': rh.registration.registration_form_id,
    }
    # Stripe-specific attributes.
    rh.stripe_token = 'xxx'
    rh.stripe_token_type = 'card'
    rh.stripe_email = 'foo@foo.com'

    request.args = {
        'registrantId': '1',
        'token': 'c6ea3f2b-062f-4371-8927-21e543be3ead',
    }
    request.form = {
        'stripeToken': rh.stripe_token,
        'stripeTokenType': rh.stripe_token_type,
        'stripeEmail': rh.stripe_email,
    }
    with StripePaymentPlugin.instance.plugin_context():
        rh._process()

    stripe_charge.assert_called_once_with(
        api_key='mock_sec_key',
        amount=stripe_amount,
        currency=curr,
        description='mock_description',
        source='xxx',
    )
    rt.assert_called_once_with(
        registration=rh.registration,
        amount=indico_amount,
        currency=curr,
        action=TransactionAction.complete,
        provider='stripe',
        data=request.form,
    )
