# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
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
from flask import request
from mock import MagicMock

from indico_payment_paypal.controllers import RHPaypalIPN
from indico_payment_paypal.plugin import PaypalPaymentPlugin


@pytest.mark.usefixtures('db', 'request_context')
@pytest.mark.parametrize(('business', 'expected'), (
    ('test', True),
    ('foo', False)
))
def test_verify_business(business, expected):
    rh = RHPaypalIPN()
    rh.event = MagicMock(id=1)
    PaypalPaymentPlugin.event_settings.set(rh.event, 'business', 'test')
    request.form = {'business': business}
    with PaypalPaymentPlugin.instance.plugin_context():
        assert rh._verify_business() == expected


@pytest.mark.usefixtures('request_context')
@pytest.mark.parametrize(('amount', 'expected'), (
    ('13.37', True),
    ('10.00', False)
))
def test_verify_amount(mocker, amount, expected):
    nai = mocker.patch('indico_payment_paypal.controllers.notify_amount_inconsistency')
    rh = RHPaypalIPN()
    rh.event = MagicMock(id=1)
    rh.registrant = MagicMock()
    rh.registrant.getTotal.return_value = 13.37
    request.form = {'mc_gross': amount}
    with PaypalPaymentPlugin.instance.plugin_context():
        assert rh._verify_amount() == expected
        assert nai.called == (not expected)
