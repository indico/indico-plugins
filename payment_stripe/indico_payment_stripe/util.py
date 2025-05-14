# This file is part of the Indico plugins.
# Copyright (C) 2019 - 2025 Various contributors + CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from decimal import Decimal

import iso4217
import stripe
from werkzeug.exceptions import NotImplemented as HTTPNotImplemented
from wtforms import ValidationError

from indico_payment_stripe import _


# These are currencies which do not need to use decimals to represent its
# smallest values.
# The values are taken from https://stripe.com/docs/currencies#zero-decimal
# as recommended by
# https://groups.google.com/a/lists.stripe.com/forum/#!topic/api-discuss/IsiAW3uEfHQ
ZERO_DECIMAL_CURRS = {
    'BIF',
    'CLP',
    'DJF',
    'GNF',
    'JPY',
    'KMF',
    'KRW',
    'MGA',
    'PYG',
    'RWF',
    'UGX',
    'VND',
    'VUV',
    'XAF',
    'XOF',
    'XPF',
}


def conv_to_stripe_amount(indico_amount: Decimal, iso_currency: str) -> int:
    """Convert from the Indico amount format to that of Stripe.

    :param indico_amount: The amount coming from Indico.
    :param str iso_currency: The ISO code of the currency being used.
    :return: The amount meant to be used by Stripe.

    In most cases, Stripe wants to see the payment amount in the given
    currency's smallest unit, unless it's a currency which does not have
    a smaller unit ("zero-decimal currencies").
    """
    iso_currency = iso_currency.upper()
    if iso_currency in ZERO_DECIMAL_CURRS:
        return int(indico_amount)
    return _to_small_currency(indico_amount, iso_currency)


def conv_from_stripe_amount(stripe_amount: int, iso_currency: str) -> Decimal:
    """Convert the given amount used for Stripe to the one used by Indico.

    :param stripe_amount: The amount used for Stripe.
    :param iso_currency: The ISO code of the currency being used.
    :return: The amount meant to be used by Indico.

    This function is the inverse of the :meth:`conv_to_stripe_amount`.
    """
    iso_currency = iso_currency.upper()
    if iso_currency in ZERO_DECIMAL_CURRS:
        return Decimal(stripe_amount)
    return _to_large_currency(stripe_amount, iso_currency)


def _validate_currency(iso_currency):
    """Check whether the currency can be properly handled by this plugin.

    :param iso_currency: an ISO4217 currency code, e.g. ``"EUR"``
    :raises: :py:exc:`~.HTTPNotImplemented` if the currency is not valid
    """
    try:
        iso4217.Currency(iso_currency)
    except ValueError:
        raise HTTPNotImplemented(
            _("Unknown currency '{}' for Stripe. Please contact the organizers.").format(iso_currency)
        )


def _to_small_currency(large_currency_amount, iso_currency) -> int:
    """Convert an amount from large currency to small currency.

    :param large_currency_amount: the amount in large currency, e.g. ``2.3``
    :param iso_currency: the ISO currency code, e.g. ``"EUR"``
    :return: the amount in small currency, e.g. ``230``
    """
    _validate_currency(iso_currency)
    exponent = iso4217.Currency(iso_currency).exponent
    return int(large_currency_amount * (10**exponent))


def _to_large_currency(small_currency_amount, iso_currency) -> Decimal:
    """Inverse of :py:func:`_to_small_currency`."""
    _validate_currency(iso_currency)
    exponent = iso4217.Currency(iso_currency).exponent
    return Decimal(small_currency_amount) / (10**exponent)


def validate_stripe_key(form, field):
    try:
        stripe.checkout.Session.list(limit=1, api_key=field.data)
    except stripe.AuthenticationError as exc:
        raise ValidationError(f'Stripe API key validation failed: {exc}')


def get_stripe_api_key(event) -> str:
    from indico_payment_stripe.plugin import StripePaymentPlugin

    if StripePaymentPlugin.event_settings.get(event, 'use_custom_key'):
        return StripePaymentPlugin.event_settings.get(event, 'stripe_api_key')
    else:
        return StripePaymentPlugin.settings.get('stripe_api_key_global')
