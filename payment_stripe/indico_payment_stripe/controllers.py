import stripe
from flask import flash, redirect, request
from flask_pluginengine import current_plugin
from markupsafe import Markup
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.controllers import RHPaymentBase
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.notifications import notify_amount_inconsistency
from indico.modules.events.payment.util import register_transaction
from indico.web.flask.util import url_for

from indico_payment_stripe import _
from indico_payment_stripe.util import conv_from_stripe_amount


class RHStripe(RHPaymentBase):
    """Processes the responses sent by Stripe."""

    def _get_event_settings(self, settings_name):
        event_settings = current_plugin.event_settings
        return event_settings.get(
            self.registration.registration_form.event,
            settings_name
        )

    def _process_args(self):
        RHPaymentBase._process_args(self)
        use_event_api_keys = self._get_event_settings('use_event_api_keys')
        self.stripe_api_key = (
            self._get_event_settings('sec_key')
            if use_event_api_keys else
            current_plugin.settings.get('sec_key')
        )

        self.session = stripe.checkout.Session.retrieve(
            request.args['session_id'],
            api_key=self.stripe_api_key
        )
        if not self.session:
            raise BadRequest('Invalid stripe session')

    def _process(self):
        payment_intent_id = self.session.payment_intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, api_key=self.stripe_api_key)

        currency = payment_intent['currency'].upper()
        amount = conv_from_stripe_amount(payment_intent['amount'], currency)
        if amount != self.registration.price or currency != self.registration.currency:
            current_plugin.logger.warning("Payment doesn't match event's fee: %s %s != %s %s",
                                          amount, currency, self.registration.price, self.registration.currency)
            notify_amount_inconsistency(self.registration, amount, currency)

        transaction_data = {k: v for k, v in payment_intent.items() if k != 'client_secret'}
        register_transaction(
            registration=self.registration,
            amount=amount,
            currency=currency,
            action=TransactionAction.complete,
            provider='stripe',
            data=transaction_data
        )

        # receipt_url = payment_intent['receipt_url']
        receipt_url = '#'
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
