# -*- coding: utf-8 -*-
"""
    controllers tests
    ~~~~~~~~~~~~~~~~~

"""

from mock import MagicMock

from flask import request

from indico_payment_stripe.controllers import RHStripe
from indico_payment_stripe.plugin import StripePaymentPlugin


def test_handler_process(mocker, db, request_context):
    rt = mocker.patch('indico_payment_stripe.controllers.register_transaction')

    stripe = mocker.patch('indico_payment_stripe.controllers.stripe')
    stripe_charge = stripe.Charge.create
    # This is a pared down return value of the API call, where we only define
    # the attributes actually used afterwards.
    stripe.Charge.create.return_value = {
        'status': 'succeeded',
        'amount': 10.01,
        'currency': 'EUR',
    }

    rh = RHStripe()
    rh.event = MagicMock(id=1)
    rh.registration = MagicMock(registration_form_id=3)
    rh.registration.getTotal.return_value = 10.01
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

    assert stripe_charge.called
    assert rt.called
