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
"""
Definition of callbacks exposed by the Indico server
"""
from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from .request_handlers import SixPayResponseHandler, UserCancelHandler, UserFailureHandler, UserSuccessHandler


#: url mount points exposing callbacks
blueprint = IndicoPluginBlueprint(
    'payment_sixpay', __name__,
    url_prefix='/event/<confId>/registrations/<int:reg_form_id>/payment/response/sixpay'
)

blueprint.add_url_rule('/failure', 'failure', UserCancelHandler, methods=('GET', 'POST'))
blueprint.add_url_rule('/cancel', 'cancel', UserFailureHandler, methods=('GET', 'POST'))
blueprint.add_url_rule('/success', 'success', UserSuccessHandler, methods=('GET', 'POST'))
# Used by SixPay to send an asynchronous notification for the transaction
blueprint.add_url_rule('/ipn', 'notify', SixPayResponseHandler, methods=('Get', 'POST'))
