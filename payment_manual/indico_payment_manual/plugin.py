# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from indico.core.plugins import IndicoPlugin, IndicoPluginBlueprint, url_for_plugin
from indico.modules.payment import PaymentPluginMixin, PaymentPluginSettingsFormBase, PaymentEventSettingsFormBase
from indico.util.i18n import _
from indico.web.forms.validators import UsedIf


DETAILS_DESC = _('The details the user needs to make their payment. This usually includes the bank account details '
                 'the IBAN and payment reference.')


class PluginSettingsForm(PaymentPluginSettingsFormBase):
    details = TextAreaField(_('Payment details'), [], description=DETAILS_DESC)


class EventSettingsForm(PaymentEventSettingsFormBase):
    details = TextAreaField(_('Payment details'), [UsedIf(lambda form, _: form.enabled.data), DataRequired()],
                            description=DETAILS_DESC)


class ManualPaymentPlugin(PaymentPluginMixin, IndicoPlugin):
    """Bank Transfer

    Provides a payment method where bank details etc. are shown to the user
    who then pays manually using e.g. a wire transfer. Marking the registrant
    as paid is then done manually by a manager of the event.
    """
    configurable = True
    settings_form = PluginSettingsForm
    event_settings_form = EventSettingsForm
    default_settings = {'method_name': 'Bank Transfer'}

    @property
    def logo_url(self):
        return url_for_plugin(self.name + '.static', filename='images/logo.png')

    def get_blueprints(self):
        return IndicoPluginBlueprint('payment_manual', __name__)
