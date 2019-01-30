# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.controllers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Controllers used by the plugin.

"""
from __future__ import unicode_literals

from decimal import Decimal

import stripe
from flask import flash, redirect, request
from flask_pluginengine import current_plugin
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH


stripe_transaction_action_mapping = {
    'succeeded': TransactionAction.complete,
    'failed': TransactionAction.reject,
    'pending': TransactionAction.pending
}


class RHStripe(RH):

    """Processes the responses sent by Stripe."""

    CSRF_ENABLED = False

    def _process_args(self):
        # TODO: Validation?
        # Stripe-specific form data.
        self.stripe_token = request.form['stripeToken']
        self.stripe_token_type = request.form['stripeTokenType']
        self.stripe_email = request.form['stripeEmail']
        # Indico-specific form data.
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest

    def _process(self):
        api_key = current_plugin.event_settings.get(
            self.registration.registration_form.event,
            'sec_key'
        )

        charge = stripe.Charge.create(
            api_key=api_key,
            # Because Stripe wants the amount in øre / cents, we need to adjust.
            amount=int(self.registration.price * 100),
            currency=self.registration.currency,
            # TODO: Use proper conference name.
            description='Registration fee for conference',
            source=self.stripe_token,
        )
        # TODO: Handle response from Stripe in full and handle exceptions.
        amount = Decimal(str(charge['amount'])) / 100
        register_transaction(
            registration=self.registration,
            amount=float(amount),
            currency=charge['currency'],
            action=stripe_transaction_action_mapping[charge['status']],
            provider='stripe',
            data=request.form,
        )

        flash('Your payment request has been processed.', 'success')
        return redirect(
            url_for(
                'event_registration.display_regform',
                self.registration.locator.registrant
            )
        )
