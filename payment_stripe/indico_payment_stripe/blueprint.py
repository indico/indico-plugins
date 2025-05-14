# This file is part of the Indico plugins.
# Copyright (C) 2019 - 2025 Various contributors + CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_stripe.controllers import RHInitStripePayment, RHStripeCancel, RHStripeSuccess


blueprint = IndicoPluginBlueprint(
    'payment_stripe',
    __name__,
    url_prefix='/event/<int:event_id>/registrations/<int:reg_form_id>/payment/response/stripe',
)

blueprint.add_url_rule('/init', 'init', RHInitStripePayment)
blueprint.add_url_rule('/success', 'success', RHStripeSuccess)
blueprint.add_url_rule('/cancel', 'cancel', RHStripeCancel)
