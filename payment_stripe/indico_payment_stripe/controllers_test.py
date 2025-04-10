from unittest.mock import MagicMock

import pytest
from flask import request

from indico.modules.events.payment.models.transactions import TransactionAction

from indico_payment_stripe.controllers import RHStripe
from indico_payment_stripe.plugin import StripePaymentPlugin


@pytest.mark.parametrize(('curr', 'indico_amount', 'stripe_amount'), (
    # Currency with decimals.
    ('EUR', 10.01, 1001),
    # Currenty without decimals.
    ('JPY', 3690, 3690),
))
@pytest.mark.parametrize(
    ('settings_value', 'org_sec_key', 'org_pub_key', 'event_sec_key', 'event_pub_key', 'eff_sec_key', 'eff_pub_key'),
    (
        # Default settings: using org keys
        (False, 'OSK', 'OPK', 'ESK', 'EPK', 'OSK', 'OPK'),
        # Custom settings: using event keys
        (True, 'OSK', 'OPK', 'ESK', 'EPK', 'ESK', 'EPK'),
    )
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
    stripe_payment_intent = stripe.PaymentIntent.retrieve

    stripe_charge = {
        'id': 1,
        'status': 'succeeded',
        'amount': stripe_amount,
        'currency': curr,
        'outcome': {
            'type': 'authorized'
        },
        'receipt_url': 'https://foo.com'
    }

    stripe.PaymentIntent.retrieve.return_value = stripe_charge

    rh = RHStripe()
    rh.event = MagicMock(id=1)
    rh.registration = MagicMock(registration_form_id=3)
    rh.registration.registration_form.event = dummy_event
    rh.registration.price = indico_amount
    rh.registration.currency = curr
    rh.registration.locator.registrant = {
        'confId': rh.event.id,
        'reg_form_id': rh.registration.registration_form_id,
        'event_id': dummy_event.id
    }

    payment_intent_id = 'pi_1DsqyX2eZvKYlo2CxTM01D6z'
    payment_session = {
        'payment_intent': payment_intent_id
    }

    rh.session = MagicMock(**payment_session)

    # Stripe-specific attributes.
    rh.stripe_token = 'xxx'
    rh.stripe_token_type = 'card'
    rh.stripe_email = 'foo@foo.com'

    request.args = {
        'registrantId': '1',
        'token': 'c6ea3f2b-062f-4371-8927-21e543be3ead',
    }
    request.form = {
        'charge_id': 1
    }

    with StripePaymentPlugin.instance.plugin_context():
        rh._process()

    stripe_payment_intent.assert_called_once_with(
        payment_intent_id
    )

    rt.assert_called_once_with(
        registration=rh.registration,
        amount=indico_amount,
        currency=curr,
        action=TransactionAction.complete,
        provider='stripe',
        data=request.form,
    )
