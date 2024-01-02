# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2024 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import dateutil.parser

from indico.core.plugins import IndicoPlugin
from indico.modules.events.payment import PaymentPluginMixin
from indico.util.date_time import now_utc

from indico_payment_sixpay.forms import EventSettingsForm, PluginSettingsForm


class SixpayPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """SIXPay Saferpay

    Provides a payment method using the SIXPay Saferpay API.
    """

    configurable = True
    #: form for default configuration across events
    settings_form = PluginSettingsForm
    #: form for configuration for specific events
    event_settings_form = EventSettingsForm
    #: global default settings - should be a reasonable default
    default_settings = {
        'method_name': 'SIXPay Saferpay',
        'url': 'https://www.saferpay.com/api/',
        'username': None,
        'password': None,
        'account_id': None,
        'order_description': '{event_title}, {regform_title}, {user_name}',
        'order_identifier': 'e{event_id}r{registration_id}',
        'notification_mail': None
    }
    #: per event default settings - use the global settings
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        'account_id': None,
        'order_description': None,
        'order_identifier': None,
        'notification_mail': None,
    }

    def get_blueprints(self):
        """Blueprint for URL endpoints with callbacks."""
        from indico_payment_sixpay.blueprint import blueprint
        return blueprint

    def is_pending_transaction_expired(self, transaction):
        if not (expiration := transaction.data.get('Init_PP_response', {}).get('Expiration')):
            return False
        return dateutil.parser.parse(expiration) <= now_utc()
