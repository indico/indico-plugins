# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.utils
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Shared utilities.

"""

from decimal import Decimal

from indico.util.i18n import make_bound_gettext


gettext = _ = make_bound_gettext('payment_stripe')


# These are currencies which do not need to use decimals to represent its
# smallest values.
# The values are taken from https://stripe.com/docs/currencies#zero-decimal
# as recommended by
# https://groups.google.com/a/lists.stripe.com/forum/#!topic/api-discuss/IsiAW3uEfHQ
ZERO_DECIMAL_CURRS = set([
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
])


def conv_to_stripe_amount(
    indico_amount,
    curr,
    zero_decimal_currs=ZERO_DECIMAL_CURRS
):
    """Converts the given Indico-stored amount to the one requested by Stripe.

    :param float indico_amount: The amount meant to be stored by Indico.
    :param str curr: The ISO code of the currency being used.
    :param zero_decimal_currs: Currencies whose amount do not need any
        conversion.
    :returns: The amount meant to be used by Stripe.
    :rtype: int.

    In most cases, Stripe wants to see the payment amount in the given
    currency's smallest unit. Most of the time this means multiplying by 100.
    Sometimes, the currency's smallest unit do not need such a conversion.

    """
    return (
        int(indico_amount) if curr.upper() in zero_decimal_currs
        else int(indico_amount * 100)
    )


def conv_from_stripe_amount(
    stripe_amount,
    curr,
    zero_decimal_currs=ZERO_DECIMAL_CURRS
):
    """Converts the given amount used for Stripe to the one used by Indico.

    :param float indico_amount: The amount used for Stripe.
    :param str curr: The ISO code of the currency being used.
    :param zero_decimal_currs: Currencies whose amount do not need any
        conversion.
    :returns: The amount meant to be used by Indico.
    :rtype: float.

    This function is the inverse of the :meth:`conv_to_strip_amount`.


    """
    return (
        float(stripe_amount)
        if curr.upper() in zero_decimal_currs else
        float(Decimal(str(stripe_amount)) / 100)
    )
