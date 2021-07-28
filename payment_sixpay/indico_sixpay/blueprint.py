# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2021 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.
"""Definition of callbacks exposed by the Indico server."""

from indico.core.plugins import IndicoPluginBlueprint

from .request_handlers import SixPayResponseHandler, UserCancelHandler, UserFailureHandler, UserSuccessHandler


#: url mount points exposing callbacks
blueprint = IndicoPluginBlueprint(
    'payment_sixpay', __name__,
    url_prefix='/event/<int:event_id>/registrations/<int:reg_form_id>/payment/response/sixpay'
)

blueprint.add_url_rule(
    '/failure', 'failure', UserCancelHandler, methods=('GET', 'POST')
)
blueprint.add_url_rule(
    '/cancel', 'cancel', UserFailureHandler, methods=('GET', 'POST')
)
blueprint.add_url_rule(
    '/success', 'success', UserSuccessHandler, methods=('GET', 'POST')
)
# Used by SixPay to send an asynchronous notification for the transaction
blueprint.add_url_rule(
    '/ipn', 'notify', SixPayResponseHandler, methods=('Get', 'POST')
)
