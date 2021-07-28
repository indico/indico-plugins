# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2021 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from urllib.parse import urljoin

import requests
from requests import RequestException

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import PaymentPluginMixin
from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction

from indico_payment_sixpay.forms import EventSettingsForm, PluginSettingsForm
from indico_payment_sixpay.util import (PROVIDER_SIXPAY, SIXPAY_JSON_API_SPEC, SIXPAY_PP_INIT_URL, get_request_header,
                                        get_terminal_id, to_small_currency)


class SixpayPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """SIXPay

    Provides a payment method using the SIXPay Saferpay API.
    """

    configurable = True
    #: form for default configuration across events
    settings_form = PluginSettingsForm
    #: form for configuration for specific events
    event_settings_form = EventSettingsForm
    #: global default settings - should be a reasonable default
    default_settings = {
        'method_name': 'SIXPay',
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

    # Dear future Maintainer,
    # - the business logic is here!
    # - see PaymentPluginMixin.render_payment_form for what `data` provides
    # - What happens here
    #   - We add `success`, `cancel` and `failure` for *sixpay* to redirect the
    #     user back to us AFTER his request
    #   - We add `notify` for *sixpay* to inform us asynchronously about
    #     the result
    #   - We send a request to initialize the pyment page to SixPay to get a
    #     request url for this transaction
    #   - We put the payment page URL and token we got into `data`
    #   - Return uses `indico_payment_sixpay/templates/event_payment_form.html`,
    #     presenting a trigger button to the user
    def adjust_payment_form_data(self, data):
        """Prepare the payment form shown to registrants."""
        global_settings = data['settings']
        transaction = self._get_transaction_parameters(data)
        init_response = self._init_payment_page(
            sixpay_url=global_settings['url'],
            transaction_data=transaction,
            credentials=(global_settings['username'], global_settings['password'])
        )
        data['payment_url'] = init_response['RedirectUrl']

        # create pending transaction and store Saferpay transaction token
        new_indico_txn = register_transaction(
            data['registration'],
            data['amount'],
            data['currency'],
            TransactionAction.pending,
            PROVIDER_SIXPAY,
            {'Init_PP_response': init_response}
        )
        if not new_indico_txn:
            # set it on the current transaction if we could not create a next one
            # this happens if we already have a pending transaction and it's incredibly
            # ugly...
            data['registration'].transaction.data = {'Init_PP_response': init_response}
        return data

    @staticmethod
    def get_field_format_map(registration):
        """Generate dict which provides registration information."""
        return {
            'user_id': registration.user_id,
            'user_name': registration.full_name,
            'user_firstname': registration.first_name,
            'user_lastname': registration.last_name,
            'event_id': registration.event_id,
            'event_title': registration.event.title,
            'registration_id': registration.id,
            'regform_title': registration.registration_form.title
        }

    def _get_transaction_parameters(self, payment_data):
        """Parameters for formulating a transaction request."""
        settings = payment_data['event_settings']
        registration = payment_data['registration']
        format_map = self.get_field_format_map(registration)
        for format_field in ('order_description', 'order_identifier'):
            payment_data[format_field] = settings[format_field].format(**format_map)

        # see the SixPay Manual
        # https://saferpay.github.io/jsonapi/#Payment_v1_PaymentPage_Initialize
        # on what these things mean
        transaction_parameters = {
            'RequestHeader': get_request_header(SIXPAY_JSON_API_SPEC, settings['account_id']),
            'TerminalId': get_terminal_id(settings['account_id']),
            'Payment': {
                'Amount': {
                    # indico handles price as largest currency, but six expects
                    # smallest. E.g. EUR: indico uses 100.2 Euro, but six
                    # expects 10020 Cent
                    'Value': str(to_small_currency(payment_data['amount'], payment_data['currency'])),
                    'CurrencyCode': payment_data['currency'],
                },
                'OrderId': payment_data['order_identifier'][:80],
                'DESCRIPTION': payment_data['order_description'][:1000],
            },
            # callbacks of the transaction - where to announce success etc., when redircting the user
            'ReturnUrls': {
                'Success': url_for_plugin('payment_sixpay.success', registration.locator.uuid, _external=True),
                'Fail': url_for_plugin('payment_sixpay.failure', registration.locator.uuid, _external=True),
                'Abort': url_for_plugin('payment_sixpay.cancel', registration.locator.uuid, _external=True)
            },
            'Notification': {
                # where to asynchronously call back from SixPay
                'NotifyUrl': url_for_plugin('payment_sixpay.notify', registration.locator.uuid, _external=True)
            }
        }
        if settings['notification_mail']:
            transaction_parameters['Notification']['MerchantEmails'] = [settings['notification_mail']]
        return transaction_parameters

    def _init_payment_page(self, sixpay_url, transaction_data, credentials):
        """Initialize payment page."""
        endpoint = urljoin(sixpay_url, SIXPAY_PP_INIT_URL)
        resp = requests.post(endpoint, json=transaction_data, auth=credentials)
        try:
            resp.raise_for_status()
        except RequestException as exc:
            self.logger.error('Could not initialize payment: %s', exc.response.text)
            raise Exception('Could not initialize payment')
        return resp.json()
