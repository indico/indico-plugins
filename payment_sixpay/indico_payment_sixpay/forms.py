# This file is part of the Indico plugins.
# Copyright (C) 2017 - 2021 Max Fischer, Martin Claus, CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from wtforms.fields import StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from indico.modules.events.payment import PaymentEventSettingsFormBase, PaymentPluginSettingsFormBase
from indico.web.forms.fields import IndicoPasswordField
from indico.web.forms.validators import IndicoRegexp

from indico_payment_sixpay import _


# XXX: Maybe this could be refactored to use the standard indico Placeholder system?
class FormatField:
    """Validator for format fields, i.e. strings with ``{key}`` placeholders.

    :param max_length: optional maximum length, checked on a test formatting
    :param field_map: keyword arguments to use for test formatting

    On validation, a test mapping is applied to the field. This ensures the
    field has a valid ``str.format`` format, and does not use illegal keys
    (as determined by ``default_field_map`` and ``field_map``).
    The ``max_length`` is validated against the test-formatted field, which
    is an estimate for an average sized input.
    """

    #: default placeholders to test length after formatting
    default_field_map = {
        'user_id': 12345,
        'user_name': 'Jane Whiteacre',
        'user_firstname': 'Jane',
        'user_lastname': 'Whiteacre',
        'event_id': 12345,
        'event_title': 'Placeholder: The Event',
        'registration_id': 12345,
        'regform_title': 'EarlyBird Registration'
    }

    def __init__(self, max_length=float('inf'), field_map=None):
        """Format field validator, i.e. strings with ``{key}`` placeholders.

        :param max_length: optional maximum length,
                           checked on a test formatting
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
        except KeyError as exc:
            raise ValidationError(_('Invalid format string key: {}').format(exc))
        except ValueError as exc:
            raise ValidationError(_('Malformed format string: {}').format(exc))
        if len(test_format) > self.max_length:
            raise ValidationError(
                _('Format string too long: shortest replacement with {len}, expected {max}')
                .format(len=len(test_format), max=self.max_length)
            )
        return True


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    """Configuration form for the Plugin across all events."""

    url = URLField(
        label=_('Saferpay JSON API URL'),
        validators=[DataRequired()],
        description=_('URL to contact the Saferpay JSON API'),
    )
    username = StringField(
        label=_('API username'),
        validators=[DataRequired()],
        description=_('The username to access the SaferPay JSON API')
    )
    password = IndicoPasswordField(
        label=_('API password'),
        validators=[DataRequired()],
        description=_('The password to access the SaferPay JSON API'),
        toggle=True,
    )
    account_id = StringField(
        label=_('Account ID'),
        validators=[
            Optional(),
            IndicoRegexp(r'^[0-9-]{0,15}$')
        ],
        description=_(
            'Default Saferpay account ID, such as "123456-12345678". '
            'Event managers will be able to override this.'
        )
    )
    order_description = StringField(
        label=_('Order Description'),
        validators=[DataRequired(), FormatField(max_length=80)],
        description=_(
            'The default description of each order in a human readable way. '
            'It is presented to the registrant during the transaction with Saferpay. '
            'Event managers will be able to override this.'
        )
    )
    order_identifier = StringField(
        label=_('Order Identifier'),
        validators=[DataRequired(), FormatField(max_length=80)],
        description=_(
            'The default identifier of each order for further processing. '
            'Event managers will be able to override this.'
        )
    )
    notification_mail = StringField(
        label=_('Notification Email'),
        validators=[Optional(), Email(), Length(0, 50)],
        description=_(
            'Emmil address to receive notifications of transactions. '
            "This is independent of Indico's own payment notifications. "
            'Event managers will be able to override this.'
        )
    )


class EventSettingsForm(PaymentEventSettingsFormBase):
    """Configuration form for the plugin for a specific event."""

    account_id = StringField(
        label=_('Account ID'),
        validators=[
            DataRequired(),
            IndicoRegexp(r'^[0-9-]{0,15}$')
        ],
        description=_('The Saferpay account ID, such as "123456-12345678".')
    )
    order_description = StringField(
        label=_('Order Description'),
        validators=[DataRequired(), FormatField(max_length=80)],
        description=_(
            'The description of each order in a human readable way. '
            'It is presented to the registrant during the transaction with Saferpay.'
        )
    )
    order_identifier = StringField(
        label=_('Order Identifier'),
        validators=[DataRequired(), FormatField(max_length=80)],
        description=_('The default identifier of each order for further processing.')
    )
    notification_mail = StringField(
        label=_('Notification Email'),
        validators=[DataRequired(), Email(), Length(0, 50)],
        description=_(
            'Emmil address to receive notifications of transactions. '
            "This is independent of Indico's own payment notifications."
        )
    )
