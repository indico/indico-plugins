from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from indico.modules.events.payment.models.transactions import TransactionAction

from indico_payment_stripe.controllers import RHStripeSuccess
from indico_payment_stripe.plugin import StripePaymentPlugin


@pytest.mark.parametrize(('curr', 'indico_amount', 'stripe_amount'), (
    # Currency with decimals
    ('EUR', Decimal('10.01'), 1001),
    # Currenty without decimals
    ('JPY', Decimal(3690), 3690),
    # Currency with more than 2 decimals
    ('JOD', Decimal('12.345'), 12345),
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

    stripe_response = {
        'id': 1,
        'status': 'succeeded',
        'amount': stripe_amount,
        'currency': curr,
        'client_secret': 'xxx',
    }

    stripe.PaymentIntent.retrieve.return_value = stripe_response

    rh = RHStripeSuccess()
    rh.stripe_api_key = 'xxx'
    rh.event = MagicMock(id=1)
    rh.registration = MagicMock(registration_form_id=3)
    rh.registration.registration_form.event = dummy_event
    rh.registration.price = indico_amount
    rh.registration.currency = curr
    rh.registration.locator.registrant = {
        'reg_form_id': rh.registration.registration_form_id,
        'event_id': dummy_event.id,
        'token': '00000000-0000-0000-0000-000000000000'
    }

    payment_intent_id = 'pi_test'
    rh.session = MagicMock(payment_intent=payment_intent_id)
    with StripePaymentPlugin.instance.plugin_context():
        rh._process()

    stripe_payment_intent.assert_called_once_with(
        payment_intent_id,
        api_key=rh.stripe_api_key,
    )

    del stripe_response['client_secret']  # this one must NOT be in the recorded data
    rt.assert_called_once_with(
        registration=rh.registration,
        amount=indico_amount,
        currency=curr,
        action=TransactionAction.complete,
        provider='stripe',
        data=stripe_response,
    )
