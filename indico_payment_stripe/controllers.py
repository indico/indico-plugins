# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.controllers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Controllers used by the plugin.

"""
from __future__ import unicode_literals

from flask import request
from flask_pluginengine import current_plugin
from indico.web.rh import RH
from indico.modules.events.registration.models.registrations import Registration
from werkzeug.exceptions import BadRequest


class RHStripe(RH):

    """Processes the responses sent by Stripe."""

    CSRF_ENABLED = False

    def _process_args(self):
        # TODO: Validation?
        # Stripe-specific form data.
        self.stripe_token = request.args['stripeToken']
        self.stripe_token_type = request.args['stripeTokenType']
        self.stripe_email = request.args['stripeEmail']
        # Indico-specific form data.
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest

    def _process(self):
        import stripe

        stripe.api_key = current_plugin.event_settings.get(
            self.registration.registration_form.event,
            'sec_key'
        )

        charge = stripe.Charge.create(
            amount=self.registration.price,
            currency=self.registration.currency,
            # TODO: Use proper conference name.
            description='Registration fee for conference',
            source=self.stripe_token,
        )
        # TODO: Handle response from Stripe.
        # TODO: Register transaction.
        print charge
