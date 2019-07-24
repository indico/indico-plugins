# -*- coding: utf-8 -*-
#
# This file is part of the SixPay Indico EPayment Plugin.
# Copyright (C) 2017 - 2018 Max Fischer
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SixPay Indico EPayment Plugin;
# if not, see <http://www.gnu.org/licenses/>.
"""Utility functions used by the Sixpay payment plugin."""
from __future__ import unicode_literals, division

import uuid

import iso4217
from werkzeug.exceptions import NotImplemented as HTTPNotImplemented
from flask_pluginengine import current_plugin

from indico.util.i18n import make_bound_gettext

#: internationalisation/localisation of strings
gettext = make_bound_gettext('payment_sixpay')

# Saferpay API details
saferpay_json_api_spec = '1.12'
saferpay_pp_init_url = 'Payment/v1/PaymentPage/Initialize'
saferpay_pp_assert_url = 'Payment/v1/PaymentPage/Assert'
saferpay_pp_capture_url = 'Payment/v1/Transaction/Capture'
saferpay_pp_cancel_url = 'Payment/v1/Transaction/Cancel'

# provider string
provider = 'sixpay'

# currencies for which the major to minor currency ratio
# is not a multiple of 10
NON_DECIMAL_CURRENCY = {'MRU', 'MGA'}


def validate_currency(iso_code):
    """Check whether the currency can be properly handled by this plugin.

    :param iso_code: an ISO4217 currency code, e.g. ``"EUR"``
    :type iso_code: basestring
    :raises: :py:exc:`~.HTTPNotImplemented` if the currency is not valid
    """
    if iso_code in NON_DECIMAL_CURRENCY:
        raise HTTPNotImplemented(
            gettext(
                "Unsupported currency '{0}' for SixPay."
                " Please contact the organisers"
            ).format(iso_code)
        )
    try:
        iso4217.Currency(iso_code)
    except ValueError:
        raise HTTPNotImplemented(
            gettext(
                "Unknown currency '{0}' for SixPay."
                " Please contact the organisers"
            ).format(iso_code)
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
    """Return request header dict.

    Contained information:
    - SpecVersion
    - CustomerId
    - RequestId
    - RetryIndicator
    """
    request_header = {
        'SpecVersion': api_spec,
        'CustomerId': get_customer_id(account_id),
        'RequestId': str(uuid.uuid4()),
        'RetryIndicator': 0,
    }
    return request_header


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


def get_setting(setting, event=None):
    """Return a configuration setting of the plugin."""
    if event:
        return (
            current_plugin.event_settings.get(event, setting)
            or current_plugin.settings.get(setting)
        )
    else:
        return current_plugin.settings.get(setting)
