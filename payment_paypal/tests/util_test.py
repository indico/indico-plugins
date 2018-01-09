# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

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
