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
from stripe import error as err
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from .utils import _


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

        event_settings = current_plugin.event_settings

        api_key = event_settings.get(
            self.registration.registration_form.event,
            'sec_key'
        )
        description = event_settings.get(
            self.registration.registration_form.event,
            'description'
        )

        # Several redirect possibilities:
        # To registration form:
        #   1. Successful payment.
        #   2. Possibly successful payment, manual review required.
        reg_url = url_for(
            'event_registration.display_regform',
            self.registration.locator.registrant
        )
        # To checkout page:
        #   1. Fail.
        chk_url = url_for(
            'payment.event_payment',
            self.registration.locator.registrant,
        )

        try:
            charge = stripe.Charge.create(
                api_key=api_key,
                # Because Stripe wants the amount in øre / cents,
                # we need to adjust.
                amount=int(self.registration.price * 100),
                currency=self.registration.currency,
                # TODO: Use proper conference name.
                description=description,
                source=self.stripe_token,
            )

        except err.APIConnectionError as e:
            current_plugin.logger.exception(e)
            flash(
                _(
                    'There was a problem connecting to Stripe.'
                    ' Please try again.'
                ),
                'error'
            )
            return redirect(chk_url)

        except err.CardError as e:
            current_plugin.logger.exception(e)
            flash(
                _('Your payment was declined. Please try again.'),
                'error'
            )
            return redirect(chk_url)

        except Exception as e:
            current_plugin.logger.exception(e)
            flash(
                _('Your payment can not be made. Please try again.'),
                'error'
            )
            return redirect(chk_url)

        outcome = charge['outcome']
        outc_type = outcome['type']
        seller_message = outcome.get('seller_message')
        flash_msg = None
        flash_type = None

        # See: https://stripe.com/docs/declines
        if outc_type == 'issuer_declined':
            flash_msg = _('Your payment failed because your card was declined.')
            flash_type = 'error'
            current_plugin.logger.error(seller_message)
            return redirect(reg_url)

        elif outc_type == 'blocked':
            flash_msg = _(
                'Your payment failed because it was classified as high risk.'
            )
            flash_type = 'error'
            current_plugin.logger.error(seller_message)
            return redirect(reg_url)

        elif outc_type == 'manual_review':
            flash_msg = _(
                'Your payment request has been processed and will be reviewed'
                ' soon.'
            )
            flash_type = 'info'

        elif outc_type == 'authorized':
            flash_msg = _('Your payment request has been processed.')
            flash_type = 'success'

        else:
            # This is actually the 'invalid' outcome type, which indicates
            # our API call is wrong.
            flash_msg = _(
                'Payment failed because something went wrong on our end.'
                ' Please notify the event contact person.'
            )
            flash_type = 'error'
            return redirect(reg_url)

        amount = Decimal(str(charge['amount'])) / 100
        register_transaction(
            registration=self.registration,
            amount=float(amount),
            currency=charge['currency'],
            action=stripe_transaction_action_mapping[charge['status']],
            provider='stripe',
            data=request.form,
        )

        flash(flash_msg, flash_type)
        return redirect(reg_url)
