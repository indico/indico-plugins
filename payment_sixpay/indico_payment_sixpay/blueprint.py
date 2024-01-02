# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2024 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_sixpay.controllers import (RHInitSixpayPayment, SixpayNotificationHandler, UserCancelHandler,
                                               UserFailureHandler, UserSuccessHandler)


blueprint = IndicoPluginBlueprint(
    'payment_sixpay', __name__,
    url_prefix='/event/<int:event_id>/registrations/<int:reg_form_id>/payment/sixpay'
)

blueprint.add_url_rule('/init', 'init', RHInitSixpayPayment, methods=('GET', 'POST'))
blueprint.add_url_rule('/failure', 'failure', UserCancelHandler, methods=('GET', 'POST'))
blueprint.add_url_rule('/cancel', 'cancel', UserFailureHandler, methods=('GET', 'POST'))
blueprint.add_url_rule('/success', 'success', UserSuccessHandler, methods=('GET', 'POST'))
blueprint.add_url_rule('/notify', 'notify', SixpayNotificationHandler, methods=('Get', 'POST'))
