# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.controllers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Controllers used by the plugin.

"""
from __future__ import unicode_literals

import stripe
from flask_pluginengine import current_plugin
from flask import flash, redirect, request, Markup
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from .utils import _, conv_from_stripe_amount

__all__ = ['RHStripe']

class RHStripe(RH):
    """Processes the responses sent by Stripe."""

    CSRF_ENABLED = False

    def _get_event_settings(self, settings_name):
        event_settings = current_plugin.event_settings
        return event_settings.get(
            self.registration.registration_form.event,
            settings_name
        )

    def _process_args(self):
        registration_uuid = request.args['registration_uuid']
        self.registration = Registration.find_first(uuid=registration_uuid)
        if not self.registration:
            raise BadRequest("Registration UUID not provided in callback")

        use_event_api_keys = self._get_event_settings('use_event_api_keys')
        stripe.api_key = (
            self._get_event_settings('sec_key')
            if use_event_api_keys else
            current_plugin.settings.get('sec_key')
        )

        self.session = stripe.checkout.Session.retrieve(
            request.args['session_id']
        )
        if not self.session:
            raise BadRequest("Invalid stripe session")

    def _process(self):
        payment_intent_id = self.session.payment_intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if len(payment_intent.charges.data) != 1:
            raise BadRequest("Charges data doesn't contain only 1 item.")
        charge = payment_intent.charges.data[0]

        transaction_data = {}
        transaction_data['charge_id'] = charge['id']
        register_transaction(
            registration=self.registration,
            amount=conv_from_stripe_amount(
                charge['amount'],
                charge['currency']
            ),
            currency=charge['currency'],
            action=TransactionAction.complete,
            provider='stripe',
            data=transaction_data
        )

        receipt_url = charge['receipt_url']
        flash_msg = Markup(_(
            'Your payment request has been processed.'
            ' See the receipt <a href="' + receipt_url + '">here</a>.'
        ))
        flash(flash_msg, 'success')
        reg_url = url_for(
            'event_registration.display_regform',
            self.registration.locator.registrant
        )
        return redirect(reg_url)
