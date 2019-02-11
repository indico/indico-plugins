# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.controllers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Controllers used by the plugin.

"""
from __future__ import unicode_literals

import stripe
from flask import flash, redirect, request, Markup
from flask_pluginengine import current_plugin
from stripe import error as err
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from .utils import _, conv_to_stripe_amount, conv_from_stripe_amount


__all__ = ['RHStripe']


STRIPE_TRX_ACTION_MAP = {
    'succeeded': TransactionAction.complete,
    'failed': TransactionAction.reject,
    'pending': TransactionAction.pending
}


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

        description = self._get_event_settings('description')
        use_event_api_keys = self._get_event_settings('use_event_api_keys')
        sec_key = (
            self._get_event_settings('sec_key')
            if use_event_api_keys else
            current_plugin.settings.get('sec_key')
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
                api_key=sec_key,
                amount=conv_to_stripe_amount(
                    self.registration.price,
                    self.registration.currency
                ),
                currency=self.registration.currency.lower(),
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
        receipt_url = None

        # See: https://stripe.com/docs/declines
        if outc_type == 'issuer_declined':
            flash_msg = _('Your payment failed because your card was declined.')
            flash_type = 'error'
            current_plugin.logger.error(seller_message)
            flash(flash_msg, flash_type)
            return redirect(reg_url)

        elif outc_type == 'blocked':
            flash_msg = _(
                'Your payment failed because it was classified as high risk.'
            )
            flash_type = 'error'
            current_plugin.logger.error(seller_message)
            flash(flash_msg, flash_type)
            return redirect(reg_url)

        elif outc_type == 'manual_review':
            receipt_url = charge['receipt_url']
            flash_msg = Markup(_(
                'Your payment request has been processed and will be reviewed'
                ' soon. See the receipt <a href="' + receipt_url + '">here</a>.'
            ))
            flash_type = 'info'

        elif outc_type == 'authorized':
            receipt_url = charge['receipt_url']
            flash_msg = Markup(_(
                'Your payment request has been processed.'
                ' See the receipt <a href="' + receipt_url + '">here</a>.'
            ))
            flash_type = 'success'

        else:
            # This is actually the 'invalid' outcome type, which indicates
            # our API call is wrong.
            flash_msg = _(
                'Payment failed because something went wrong on our end.'
                ' Please notify the event contact person.'
            )
            flash_type = 'error'
            flash(flash_msg, flash_type)
            return redirect(reg_url)

        register_transaction(
            registration=self.registration,
            amount=conv_from_stripe_amount(
                charge['amount'],
                charge['currency']
            ),
            currency=charge['currency'],
            action=STRIPE_TRX_ACTION_MAP[charge['status']],
            provider='stripe',
            data=request.form,
        )

        flash(flash_msg, flash_type)
        return redirect(reg_url)
