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
    # Currency with decimals.
    ('EUR', 10.01, 1001),
    # Currenty without decimals.
    ('JPY', 3690, 3690),
])
@pytest.mark.parametrize(
    'settings_value, org_sec_key, org_pub_key, event_sec_key, event_pub_key,'
    'eff_sec_key, eff_pub_key',
    [
        # Default settings: using org keys
        (False, 'OSK', 'OPK', 'ESK', 'EPK', 'OSK', 'OPK'),
        # Custom settings: using event keys
        (True, 'OSK', 'OPK', 'ESK', 'EPK', 'ESK', 'EPK'),
    ]
)
def test_handler_process(
    curr, indico_amount, stripe_amount,
    settings_value, org_sec_key, org_pub_key, event_sec_key, event_pub_key,
    eff_sec_key, eff_pub_key,
    mocker, db, dummy_event, request_context,
):

    StripePaymentPlugin.settings.set('sec_key', org_sec_key)
    StripePaymentPlugin.settings.set('pub_key', org_pub_key)
    StripePaymentPlugin.event_settings.set(
        dummy_event,
        'use_event_api_keys',
        settings_value,
    )
    StripePaymentPlugin.event_settings.set(
        dummy_event,
        'sec_key',
        event_sec_key,
    )
    StripePaymentPlugin.event_settings.set(
        dummy_event,
        'pub_key',
        event_pub_key,
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
        api_key=eff_sec_key,
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
