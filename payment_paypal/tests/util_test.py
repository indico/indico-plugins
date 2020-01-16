# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import pytest
from mock import MagicMock
from wtforms import ValidationError

from indico_payment_paypal.util import validate_business


@pytest.mark.parametrize(('data', 'valid'), (
    ('foobar',              False),
    ('foo@bar,com',         False),
    ('example@example.com', True),
    ('X2345A789B12Cx',      False),
    ('X2345A789B12',        False),
    ('1234567890123',       True),
    ('X2345A789B12C',       True),
))
def test_validate_business(data, valid):
    field = MagicMock(data=data)
    if valid:
        validate_business(None, field)
    else:
        with pytest.raises(ValidationError):
            validate_business(None, field)
