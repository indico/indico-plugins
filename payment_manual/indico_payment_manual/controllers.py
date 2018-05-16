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

from __future__ import unicode_literals

from flask import flash, redirect, request, session
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.modules.events.registration.controllers.management import RHManageRegFormsBase
from indico.web.flask.util import url_for
from indico.web.flask.templating import get_template_module
from indico.web.rh import RH
from indico.web.util import jsonify_data

from indico_payment_paypal import _


class RHManualConfirm(RH):
    """Process the manual confirmation by the user"""

    def _process_args(self):
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest

    def _process(self):
        register_transaction(registration=self.registration,
                             amount=self.registration.price,
                             currency=self.registration.currency,
                             action=TransactionAction.pending,
                             provider='manual',
                             data={})

        flash(_('Please wait two to three business days until we have received your payment.'), 'info')
        return redirect(url_for('event_registration.display_regform', self.registration.locator.registrant))


class RHManualReceived(RHManageRegFormsBase):
    """Modify the payment status of a registration"""

    def _process_args(self):
        self.token = request.args['token']
        self.registration = Registration.find_first(uuid=self.token)
        if not self.registration:
            raise BadRequest
        self.event = self.registration.event

    def _process(self):
        register_transaction(registration=self.registration,
                             amount=self.registration.transaction.amount,
                             currency=self.registration.transaction.currency,
                             action=TransactionAction.complete,
                             provider='manual',
                             data={'changed_by_name': session.user.full_name,
                                   'changed_by_id': session.user.id})
        return redirect(url_for('event_registration.registration_details', self.registration))

