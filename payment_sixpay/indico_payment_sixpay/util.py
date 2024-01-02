# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2024 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import uuid

import iso4217
from werkzeug.exceptions import NotImplemented as HTTPNotImplemented

from indico_payment_sixpay import _


# Saferpay API details
SIXPAY_JSON_API_SPEC = '1.12'
SIXPAY_PP_INIT_URL = 'Payment/v1/PaymentPage/Initialize'
SIXPAY_PP_ASSERT_URL = 'Payment/v1/PaymentPage/Assert'
SIXPAY_PP_CAPTURE_URL = 'Payment/v1/Transaction/Capture'
SIXPAY_PP_CANCEL_URL = 'Payment/v1/Transaction/Cancel'

# payment provider identifier
PROVIDER_SIXPAY = 'sixpay'

# currencies for which the major to minor currency ratio
# is not a multiple of 10
NON_DECIMAL_CURRENCY = {'MRU', 'MGA'}


def validate_currency(iso_code):
    """Check whether the currency can be properly handled by this plugin.

    :param iso_code: an ISO4217 currency code, e.g. ``"EUR"``
    :raises: :py:exc:`~.HTTPNotImplemented` if the currency is not valid
    """
    if iso_code in NON_DECIMAL_CURRENCY:
        raise HTTPNotImplemented(
            _("Unsupported currency '{}' for SIXPay. Please contact the organizers").format(iso_code)
        )
    try:
        iso4217.Currency(iso_code)
    except ValueError:
        raise HTTPNotImplemented(
            _("Unknown currency '{}' for SIXPay. Please contact the organizers").format(iso_code)
        )


def to_small_currency(large_currency_amount, iso_code):
    """Convert an amount from large currency to small currency.

    :param large_currency_amount: the amount in large currency, e.g. ``2.3``
    :param iso_code: the ISO currency code, e.g. ``"EUR"``
    :return: the amount in small currency, e.g. ``230``
    """
    validate_currency(iso_code)
    exponent = iso4217.Currency(iso_code).exponent
    if exponent == 0:
        return large_currency_amount
    return int(large_currency_amount * (10 ** exponent))


def to_large_currency(small_currency_amount, iso_code):
    """Inverse of :py:func:`to_small_currency`."""
    validate_currency(iso_code)
    exponent = iso4217.Currency(iso_code).exponent
    if exponent == 0:
        return small_currency_amount
    return small_currency_amount / (10 ** exponent)


def get_request_header(api_spec, account_id):
    return {
        'SpecVersion': api_spec,
        'CustomerId': get_customer_id(account_id),
        'RequestId': str(uuid.uuid4()),
        'RetryIndicator': 0,
    }


def get_customer_id(account_id):
    """Extract customer ID from account ID.

    Customer ID is the first part (befor the hyphen) of the account ID.
    """
    return account_id.split('-')[0]


def get_terminal_id(account_id):
    """Extract the teminal ID from account ID.

    The Terminal ID is the second part (after the hyphen) of the
    account ID.
    """
    return account_id.split('-')[1]
