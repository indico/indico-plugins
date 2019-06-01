# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_payfast.controllers import RHPayfastCancel, RHPayfastIPN, RHPayfastSuccess


blueprint = IndicoPluginBlueprint('payment_payfast', __name__,
                                  url_prefix='/event/<confId>/registrations/<int:reg_form_id>/payment/response/payfast')

blueprint.add_url_rule('/cancel', 'cancel', RHPayfastCancel, methods=('GET', 'POST'))
blueprint.add_url_rule('/success', 'success', RHPayfastSuccess, methods=('GET', 'POST'))
# Used by PayPal to send an asynchronous notification for the transaction (pending, successful, etc)
blueprint.add_url_rule('/ipn', 'notify', RHPayfastIPN, methods=('POST',))
