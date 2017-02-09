# -*- coding: utf-8 -*-
##
## This file is part of the SixPay Indico EPayment Plugin.
## Copyright (C) 2017 - 2018 Max Fischer
##
## This is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## This software is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with SixPay Indico EPayment Plugin;if not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals, division

import iso4217
from werkzeug.exceptions import NotImplemented as HTTPNotImplemented

from indico.util.i18n import make_bound_gettext

#: internationalisation/localisation of strings
gettext = make_bound_gettext('payment_sixpay')


#: currencies for which the major to minor currency ratio is not a multiple of 10
NON_DECIMAL_CURRENCY = {'MRU', 'MGA'}


def validate_currency(iso_code):
    """
    Check whether the currency can be properly handled by this plugin

    :param iso_code: an ISO4217 currency code, e.g. ``"EUR"``
    :type iso_code: basestring
    :raises: :py:exc:`~.HTTPNotImplemented` if the currency is not valid
    """
    if iso_code in NON_DECIMAL_CURRENCY:
        raise HTTPNotImplemented(
            gettext("Unsupported currency '{0}' for SixPay. Please contact the organisers").format(iso_code)
        )
    try:
        iso4217.Currency(iso_code)
    except ValueError:
        raise HTTPNotImplemented(
            gettext("Unknown currency '{0}' for SixPay. Please contact the organisers").format(iso_code)
        )


def to_small_currency(large_currency_amount, iso_code):
    """
    Convert an amount from large currency to small currency, e.g. 2.3 Euro to 230 Eurocent

    :param large_currency_amount: the amount in large currency, e.g. ``2.3``
    :param iso_code: the ISO currency code, e.g. ``"EUR"``
    :return: the amount in small currency, e.g. ``230``
    """
    validate_currency(iso_code)
    exponent = iso4217.Currency(iso_code).exponent
    if exponent == 0:
        return large_currency_amount
    return large_currency_amount * (10 ** exponent)


def to_large_currency(small_currency_amount, iso_code):
    """Inverse of :py:func:`to_small_currency`"""
    validate_currency(iso_code)
    exponent = iso4217.Currency(iso_code).exponent
    if exponent == 0:
        return small_currency_amount
    return small_currency_amount / (10 ** exponent)
