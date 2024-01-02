# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from decimal import Decimal
from urllib.parse import quote_plus

from indico.modules.events.registration.placeholders.registrations import IDPlaceholder
from indico.util.placeholders import ParametrizedPlaceholder, Placeholder

from indico_payment_manual import _


class EscapablePlaceholder(ParametrizedPlaceholder):
    param_required = False
    param_restricted = True
    field = None
    basic_description = None

    @classmethod
    def render(cls, param, regform, registration):
        rv = getattr(registration, cls.field)
        if param == 'url':
            rv = quote_plus(rv)
        return rv

    @classmethod
    def iter_param_info(cls, regform, registration):
        yield None, cls.basic_description
        yield 'url', '{} ({})'.format(cls.basic_description, _('escaped for URLs'))


class FirstNamePlaceholder(EscapablePlaceholder):
    name = 'first_name'
    basic_description = _('First name of the registrant')
    field = 'first_name'


class LastNamePlaceholder(EscapablePlaceholder):
    name = 'last_name'
    basic_description = _('Last name of the registrant')
    field = 'last_name'


class EmailPlaceholder(EscapablePlaceholder):
    name = 'email'
    basic_description = _('Email address of the registrant')
    field = 'email'


class RegistrationIDPlaceholder(IDPlaceholder):
    name = 'registration_id'


class RegistrationDatabaseIDPlaceholder(Placeholder):
    name = 'registration_db_id'
    description = _('The database ID of the registration')

    @classmethod
    def render(cls, regform, registration):
        return registration.id


class RegistrationFormIDPlaceholder(Placeholder):
    name = 'registration_form_id'
    description = _('The ID of the registration form')

    @classmethod
    def render(cls, regform, registration):
        return registration.registration_form.id


class EventIDPlaceholder(Placeholder):
    name = 'event_id'
    description = _('The ID of the event')

    @classmethod
    def render(cls, regform, registration):
        return registration.registration_form.event.id


class PricePlaceholder(ParametrizedPlaceholder):
    param_required = False
    param_restricted = True
    name = 'price'

    @classmethod
    def render(cls, param, regform, registration):
        if param == 'int':
            return str(int(registration.price * 100))
        elif param == 'short' and int(registration.price) == registration.price:
            return str(int(registration.price))
        else:
            return str(registration.price.quantize(Decimal('.01')))

    @classmethod
    def iter_param_info(cls, regform, registration):
        yield None, _('The price the registrant needs to pay (e.g. 100.00 or 100.25)')
        yield 'short', _('The price without cents if possible (e.g. 100 or 100.25)')
        yield 'int', _('The price formatted as an integer (e.g. 10000 or 10025)')


class CurrencyPlaceholder(Placeholder):
    name = 'currency'
    description = _('The currency used in the registration')

    @classmethod
    def render(cls, regform, registration):
        return registration.currency
