# This file is part of the Indico plugins.
# Copyright (C) 2019 - 2025 Various contributors + CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import stripe
from flask import flash, redirect
from marshmallow import fields
from werkzeug.exceptions import BadRequest, NotFound

from indico.core.errors import IndicoError
from indico.core.plugins import url_for_plugin
from indico.modules.events.payment.controllers import RHPaymentBase
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.notifications import notify_amount_inconsistency
from indico.modules.events.payment.util import get_active_payment_plugins, register_transaction
from indico.web.args import use_kwargs
from indico.web.flask.util import url_for

from indico_payment_stripe import _
from indico_payment_stripe.plugin import StripePaymentPlugin
from indico_payment_stripe.util import conv_from_stripe_amount, conv_to_stripe_amount, get_stripe_api_key


class RHInitStripePayment(RHPaymentBase):
    """Initialize a Stripe payment and redirect to Stripe."""

    def _process_args(self):
        RHPaymentBase._process_args(self)
        if 'stripe' not in get_active_payment_plugins(self.event):
            raise NotFound
        if not StripePaymentPlugin.instance.supports_currency(self.registration.currency):
            raise BadRequest

    def _process(self):
        if not (api_key := get_stripe_api_key(self.event)):
            raise IndicoError('Stripe is not correctly configured in this event. Please contact the organizers.')
        price = conv_to_stripe_amount(self.registration.price, self.registration.currency)
        name = self.registration.event.title
        description = self.registration.registration_form.title

        # pass the registration uuid explicitly all the time, since the redirect after a successful
        # payment is crucial for marking it as paid on Indico, and we do not want to deal with the
        # (albeit unlikely) case that someone's session expired in the meantime.
        # we need the "double placeholder" because the curly braces get url-encoded by `url_for`,
        # but we need to keep them intact as the stripe library replaces them
        success_url = url_for_plugin(
            'payment_stripe.success', self.registration.locator.uuid, stripe_session_id='__sid__', _external=True
        ).replace('__sid__', '{CHECKOUT_SESSION_ID}')
        cancel_url = url_for_plugin('payment_stripe.cancel', self.registration.locator.registrant, _external=True)

        metadata = {
            # XXX: metadata values are always strings
            'indico_event_id': str(self.registration.event.id),
            'indico_registration_id': str(self.registration.id),
            'indico_registration_form_id': str(self.registration.registration_form.id),
            'indico_registration_last_txn': (
                str(self.registration.transaction.id if self.registration.transaction else -1)
            ),
        }

        stripe_session = stripe.checkout.Session.create(
            mode='payment',
            customer_email=self.registration.email,
            metadata=metadata,
            payment_intent_data={
                'description': (
                    f'Indico: {self.registration.event.id}#{self.registration.friendly_id} '
                    f'({self.registration.full_name})'
                ),
                'metadata': metadata,
            },
            line_items=[
                {
                    'quantity': 1,
                    'price_data': {
                        'currency': self.registration.currency,
                        'unit_amount': price,
                        'product_data': {
                            'name': name,
                            'description': description,
                        },
                    },
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            api_key=api_key,
        )
        return redirect(stripe_session.url)


class RHStripeCancel(RHPaymentBase):
    """Process a cancellation sent by Stripe.

    This happens when the user uses the "back" button on the Stripe payment page.
    """

    def _process(self):
        flash(_('You cancelled the payment.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class RHStripeSuccess(RHPaymentBase):
    """Process the success response sent by Stripe."""

    @use_kwargs({'stripe_session_id': fields.String(required=True)}, location='query')
    def _process_args(self, stripe_session_id):
        RHPaymentBase._process_args(self)
        self.stripe_api_key = get_stripe_api_key(self.event)
        self.stripe_session = stripe.checkout.Session.retrieve(stripe_session_id, api_key=self.stripe_api_key)
        if not self.stripe_session:
            raise BadRequest('Invalid stripe session')

    def _process(self):
        expected_txn_id = str(self.registration.transaction.id if self.registration.transaction else -1)

        # stripe session belongs to a different registration
        if self.stripe_session.metadata['indico_registration_id'] != str(self.registration.id):
            raise BadRequest('Invalid stripe session metadata')
        # registration had a transaction registered since initiating the payment process
        elif self.stripe_session.metadata['indico_registration_last_txn'] != expected_txn_id:
            raise BadRequest('Invalid registration transaction state')
        payment_intent_id = self.stripe_session.payment_intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, api_key=self.stripe_api_key)
        payment_method = stripe.PaymentMethod.retrieve(payment_intent.payment_method, api_key=self.stripe_api_key)

        currency = payment_intent['currency'].upper()
        amount = conv_from_stripe_amount(payment_intent['amount'], currency)
        if amount != self.registration.price or currency != self.registration.currency:
            StripePaymentPlugin.logger.warning(
                "Payment doesn't match event's fee: %s %s != %s %s",
                amount,
                currency,
                self.registration.price,
                self.registration.currency,
            )
            notify_amount_inconsistency(self.registration, amount, currency)

        transaction_data = {
            'checkout_session': dict(self.stripe_session),
            'payment_intent': {k: v for k, v in payment_intent.items() if k != 'client_secret'},
            'payment_method': dict(payment_method),
        }
        register_transaction(
            registration=self.registration,
            amount=amount,
            currency=currency,
            action=TransactionAction.complete,
            provider='stripe',
            data=transaction_data,
        )

        flash(_('Your payment was successful.'), 'success')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))
