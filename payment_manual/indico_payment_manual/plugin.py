# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from wtforms.fields.simple import TextAreaField
from wtforms.validators import DataRequired

from indico.core import signals
from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from indico.modules.events.payment import (PaymentEventSettingsFormBase, PaymentPluginMixin,
                                           PaymentPluginSettingsFormBase)
from indico.util.placeholders import render_placeholder_info, replace_placeholders
from indico.web.forms.validators import UsedIf

from indico_payment_manual import _


DETAILS_DESC = _('The details the user needs to make their payment. This usually includes the bank account details, '
                 'the IBAN and payment reference.  You can also link to a custom payment site. In this case make sure '
                 'to use the URL-escaped versions of the placeholders where available.')


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    details = TextAreaField(_('Payment details'), [])

    def __init__(self, *args, **kwargs):
        super(PluginSettingsForm, self).__init__(*args, **kwargs)
        self.details.description = DETAILS_DESC + '\n' + render_placeholder_info('manual-payment-details',
                                                                                 regform=None, registration=None)


class EventSettingsForm(PaymentEventSettingsFormBase):
    details = TextAreaField(_('Payment details'), [UsedIf(lambda form, _: form.enabled.data), DataRequired()])

    def __init__(self, *args, **kwargs):
        super(EventSettingsForm, self).__init__(*args, **kwargs)
        self.details.description = DETAILS_DESC + '\n' + render_placeholder_info('manual-payment-details',
                                                                                 regform=None, registration=None)


class ManualPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Bank Transfer

    Provides a payment method where bank details etc. are shown to the user
    who then pays manually using e.g. a wire transfer. Marking the registrant
    as paid is then done manually by a manager of the event.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {'method_name': 'Bank Transfer',
                        'details': ''}
    default_event_settings = {'enabled': False,
                              'method_name': None,
                              'details': ''}

    def init(self):
        super(ManualPaymentPlugin, self).init()
        self.connect(signals.get_placeholders, self._get_details_placeholders, sender='manual-payment-details')

    def _get_details_placeholders(self, sender, regform, registration, **kwargs):
        from indico_payment_manual.placeholders import (FirstNamePlaceholder, LastNamePlaceholder,
                                                        RegistrationIDPlaceholder, EventIDPlaceholder, PricePlaceholder,
                                                        CurrencyPlaceholder)
        yield FirstNamePlaceholder
        yield LastNamePlaceholder
        yield RegistrationIDPlaceholder
        yield EventIDPlaceholder
        yield PricePlaceholder
        yield CurrencyPlaceholder

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        return IndicoPluginBlueprint('payment_manual', __name__)

    def adjust_payment_form_data(self, data):
        data['details'] = replace_placeholders('manual-payment-details', data['event_settings']['details'],
                                               regform=data['registration'].registration_form,
                                               registration=data['registration'])
