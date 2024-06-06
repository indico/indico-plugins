# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import re

from wtforms import ValidationError

from indico.util.string import is_valid_mail

from indico_payment_paypal import _


def validate_business(form, field):
    """Validates a PayPal business string.

    It can either be an email address or a paypal business account ID.
    """
    if not is_valid_mail(field.data, multi=False) and not re.match(r'^[a-zA-Z0-9]{13}$', field.data):
        raise ValidationError(_('Invalid email address / paypal ID'))

def validate_paypal_fixed_fee(form, field):
    """Validates a PayPal fixed fee value.

    It can either any float number greater or equal 0
    """
    if not re.match(r'^[0-9]+(\.[0-9]+)?$', field.data):
        raise ValidationError(_('Invalid PayPal Fixed Fee value'))

def validate_paypal_percent_fee(form, field):
    """Validates a PayPal percent fee value.

    It can either any float number greater or equal 0 followed by an optional %
    """
    if not re.match(r'^[0-9]+(\.[0-9]+)?(%)?$', field.data):
        raise ValidationError(_('Invalid PayPal Percent Fee value'))
