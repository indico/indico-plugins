# -*- coding: utf-8 -*-
# This file is part of the SixPay Indico EPayment Plugin.
# Copyright (C) 2017 - 2018 Max Fischer
#
# This is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SixPay Indico EPayment Plugin;
# if not, see <http://www.gnu.org/licenses/>.
"""
Core of the SixPay plugin.

The entry point for indico is the :py:class:`~.SixpayPaymentPlugin`.
It handles configuration via the settings forms, initiates payments
and provides callbacks for finished payments via its blueprint.
"""
from __future__ import unicode_literals, absolute_import
import urlparse

import requests
from werkzeug.exceptions import (
    NotImplemented as HTTPNotImplemented,
    InternalServerError as HTTPInternalServerError
)

from wtforms.fields import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import (
    DataRequired, Optional, Regexp, Length, Email, ValidationError
)
from indico.web.forms.fields import IndicoPasswordField

from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.payment import (
    PaymentEventSettingsFormBase,
    PaymentPluginMixin,
    PaymentPluginSettingsFormBase)
from indico.modules.events.payment.models.transactions import (
    PaymentTransaction,
    TransactionAction
)


from .utility import (
    gettext, to_small_currency, get_request_header, get_terminal_id,
    provider
)
# blueprint mounts the request handlers onto URLs
from .blueprint import blueprint

from .utility import saferpay_json_api_spec, saferpay_pp_init_url

# Dear Future Maintainer,
#
# while an improvement over Indico 1.2, the Indico 2.0 plugin/core
# facilities are rather lacking in documentation. I have added
# some notes for each **base**type on how they are integrated with
# the rest of Indico. Be aware that this is reconstructed from
# implementations, not from official API docs.
#
# Regards,
# Past Maintainer


# PaymentPluginSettingsFormBase from indico.modules.events.payment
# - A codified Form for users to fill in. The *class attributes* define
#   which fields exist, their shape, description, etc.
# - Each field is a type from wtforms.fields.core.Field. You probably want:
#   - label: Name of the field, an internationalised identifier
#   - validators: Input validation, see wtforms.validators
#   - description: help text of the field, an internationalised text

class FormatField(object):
    """Validator for format fields, i.e. strings with ``{key}`` placeholders.

    :param max_length: optional maximum length, checked on a test formatting
    :type max_length: int
    :param field_map: keyword arguments to use for test formatting

    On validation, a test mapping is applied to the field. This ensures the
    field has a valid ``str.format`` format, and does not use illegal keys
    (as determined by ``default_field_map`` and ``field_map``).
    The ``max_length`` is validated against the test-formatted field, which
    is an estimate for an average sized input.
    """

    #: default placeholders to test length after formatting
    default_field_map = {
        'user_id': 1234,
        'user_name': 'Jane Whiteacre',
        'event_id': 123,
        'event_title': 'Placeholder: The Event',
        'eventuser_id': 'e123u1234',
        'registration_title': 'EarlyBird Registration'
    }

    def __init__(self, max_length=float('inf'), field_map=None):
        """Format field validator, i.e. strings with ``{key}`` placeholders.

        :param max_length: optional maximum length,
                           checked on a test formatting
        :type max_length: int
        :param field_map: keyword arguments to use for test formatting
        """
        self.max_length = max_length
        self.field_map = self.default_field_map.copy()
        if field_map is not None:
            self.field_map.update(field_map)

    def __call__(self, form, field):
        """Validate format field data.

        Returns true on successful validation, else an ValidationError is
        thrown.
        """
        if not field.data:
            return True
        try:
            test_format = field.data.format(**self.field_map)
        except KeyError as err:
            raise ValidationError('Invalid format string key: {}'.format(err))
        except ValueError as err:
            raise ValidationError('Malformed format string: {}'.format(err))
        if len(test_format) > self.max_length:
            raise ValidationError(
                'Too long format string:'
                ' shortest replacement with {0}, expected {1}'
                .format(
                    len(test_format), self.max_length
                )
            )
        else:
            return True


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    """Configuration form for the Plugin across all events."""

    url = URLField(
        label=gettext('SixPay Saferpay URL'),
        validators=[DataRequired()],
        description=gettext('URL to contact the Six Payment Service'),
    )
    username = StringField(
        label=gettext('Username'),
        validators=[DataRequired()],
        description=gettext('SaferPay JSON API User name.')
    )
    password = IndicoPasswordField(
        label=gettext('Password'),
        validators=[DataRequired()],
        description=gettext('SaferPay JSON API User password.'),
        toggle=True,
    )
    account_id = StringField(
        label='Account ID',
        # can be set EITHER or BOTH globally and per event
        validators=[
            Optional(),
            Regexp(
                r'[0-9-]{0,15}',
                message='Field must contain up to 15 digits or "-".'
            )
        ],
        description=gettext(
            'Default ID of your Saferpay account,'
            ' such as "401860-17795278".'
        )
    )
    order_description = StringField(
        label=gettext('Order Description'),
        validators=[DataRequired(), FormatField(max_length=80)],
        description=gettext(
            'The description of each order in a human readable way. '
            'This description is presented to the registrant during the '
            'transaction with SixPay.'
        )
    )
    order_identifier = StringField(
        label=gettext('Order Identifier'),
        validators=[DataRequired(), FormatField(max_length=80)],
        description=gettext(
            'The identifier of each order for further processing.'
        )
    )
    notification_mail = StringField(
        label=gettext('Notification Email'),
        validators=[Optional(), Email(), Length(0, 50)],
        description=gettext(
            'Mail address to receive notifications of transactions.'
            'This is independent of Indico\'s own payment notifications.'
        )
    )


class EventSettingsForm(PaymentEventSettingsFormBase):
    """Configuration form for the Plugin for a specific event."""

    # every setting may be overwritten for each event
    #url = PluginSettingsForm.url
    #username = PluginSettingsForm.username
    #password = PluginSettingsForm.password
    account_id = PluginSettingsForm.account_id
    order_description = PluginSettingsForm.order_description
    order_identifier = PluginSettingsForm.order_identifier
    notification_mail = PluginSettingsForm.notification_mail


# PaymentPluginMixin, IndicoPlugin
# This is basically a registry of setting fields,
# logos and other rendering stuff.
# All the business logic is in :py:func:`adjust_payment_form_data`
class SixpayPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """SixPay Saferpay plugin.

    Provides an EPayment method using the SixPay Saferpay API.
    """

    configurable = True
    #: form for default configuration across events
    settings_form = PluginSettingsForm
    #: form for configuration for specific events
    event_settings_form = EventSettingsForm
    #: global default settings - should be a reasonable default
    default_settings = {
        'method_name': 'SixPay',
        'url': 'https://www.saferpay.com/api/',
        'username': None,
        'password': None,
        'account_id': None,
        'order_description':
            '{event_title}, {registration_title}, {user_name}',
        'order_identifier': '{eventuser_id}',
        'notification_mail': None
    }
    #: per event default settings - use the global settings
    default_event_settings = {
        'enabled': False,
        'method_name': None,
        # 'url': None,
        # 'username': None,
        # 'password': None,
        'account_id': None,
        'order_description': None,
        'order_identifier': None,
        'notification_mail': None,
    }

    def get_blueprints(self):
        """Blueprint for URL endpoints with callbacks."""
        return blueprint

    # Dear Future Maintainer,
    # - business logic is here!
    # - see PaymentPluginMixin.render_payment_form for what `data` provides
    # - What happens here
    #   - We add `success`, `cancel` and `failure` for *sixpay* to redirect the
    #     user back to us AFTER his request
    #   - We add `notify` for *sixpay* to inform us asynchronously about
    #     the result
    #   - We send a request to initialize the pyment page to SixPay to get a
    #     request url for this transaction
    #   - We put the payment page URL and token we got into `data`
    #   - Return uses `indico_sixpay/templates/event_payment_form.html`,
    #     presenting a trigger button to the user
    def adjust_payment_form_data(self, data):
        """Prepare the payment form shown to registrants."""
        # indico does not seem to provide stacking of settings
        # we merge event on top of global settings, but remove defaults
        event_settings = data['event_settings']
        global_settings = data['settings']
        plugin_settings = {
            key: event_settings[key]
            if event_settings.get(key) is not None
            else global_settings[key]
            for key in (set(event_settings) | set(global_settings))
        }
        # parameters of the transaction - amount, currency, ...
        transaction = self._get_transaction_parameters(data, plugin_settings)
        init_response = self._init_payment_page(
            sixpay_url=plugin_settings['url'],
            transaction_data=transaction,
            credentials=(
                plugin_settings['username'], plugin_settings['password'])
        )
        data['payment_url'] = init_response['RedirectUrl']

        # create pending transaction and store Saferpay transaction token
        if not PaymentTransaction.create_next(
            registration=data['registration'],
            amount=data['amount'],
            currency=data['currency'],
            action=TransactionAction.pending,
            provider=provider,
            data={'Init_PP_response': init_response}
        ):
            data['registration'].transaction.data = {
                'Init_PP_response': init_response
            }
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
            'eventuser_id':
                'e{0}u{1}'.format(registration.event_id, registration.user_id),
            'registration_title': registration.registration_form.title
        }

    def _get_transaction_parameters(self, payment_data, plugin_settings):
        """Parameters for formulating a transaction request."""
        registration = payment_data['registration']
        format_map = self.get_field_format_map(registration)
        for format_field in 'order_description', 'order_identifier':
            try:
                payment_data[format_field] = (
                    plugin_settings[format_field].format(**format_map)
                )
            except ValueError:
                message = (
                    "Invalid format field placeholder for {0},"
                    " please contact the event organisers!"
                )
                raise HTTPNotImplemented(
                    (gettext(message) + '\n\n[' + message + ']')
                    .format(self.name)
                 )
            except KeyError:
                message = (
                    'Unknown format field placeholder "{0}" for {1},'
                    ' please contact the event organisers!'
                )
                raise HTTPNotImplemented((
                        gettext(message) + '\n\n[' + message + ']'
                    ).format(format_field, self.name)
                )

        # see the SixPay Manual
        # https://saferpay.github.io/jsonapi/#Payment_v1_PaymentPage_Initialize
        # on what these things mean
        transaction_parameters = {
            'RequestHeader': get_request_header(
                saferpay_json_api_spec, plugin_settings['account_id']
            ),
            'TerminalId': str(
                get_terminal_id(plugin_settings['account_id'])
            ),
            'Payment': {
                'Amount': {
                    # indico handles price as largest currency, but six expects
                    # smallest. E.g. EUR: indico uses 100.2 Euro, but six
                    # expects 10020 Cent
                    'Value': '{:d}'.format(
                        to_small_currency(
                            payment_data['amount'],
                            payment_data['currency']
                        )
                    ),
                    'CurrencyCode': payment_data['currency'],
                },
                'OrderId': payment_data['order_identifier'][:80],
                'DESCRIPTION': payment_data['order_description'][:1000],
            },
            # callbacks of the transaction - where to announce success, ...
            # where to redirect the user
            'ReturnUrls': {
                'Success': url_for_plugin(
                    'payment_sixpay.success',
                    registration.locator.uuid,
                    _external=True
                ),
                'Fail': url_for_plugin(
                    'payment_sixpay.failure',
                    registration.locator.uuid,
                    _external=True
                ),
                'Abort': url_for_plugin(
                    'payment_sixpay.cancel',
                    registration.locator.uuid,
                    _external=True
                )
            },
            'Notification': {
                # where to asynchronously call back from SixPay
                'NotifyUrl': url_for_plugin(
                    'payment_sixpay.notify',
                    registration.locator.uuid,
                    _external=True
                )
            }
        }
        if 'notification_mail' in plugin_settings:
            transaction_parameters['Notification']['MerchantEmails'] = (
                plugin_settings['notification_mail']
            )
        return transaction_parameters

    def _init_payment_page(self, sixpay_url, transaction_data, credentials):
        """Initialize payment page."""
        endpoint = urlparse.urljoin(sixpay_url, saferpay_pp_init_url)
        url_request = requests.post(
            endpoint,
            json=transaction_data,
            auth=credentials
        )
        # raise any HTTP errors
        url_request.raise_for_status()
        response = url_request.json()
        if 'ErrorName' in response:
            if 'ErrorDetail' not in response:
                response['ErrorDetail'] = ''
            raise HTTPInternalServerError(
                'Failed request to SixPay service:'
                ' {ErrorMessage}. {ErrorDetail}'
                .format(response)
            )
        return response
