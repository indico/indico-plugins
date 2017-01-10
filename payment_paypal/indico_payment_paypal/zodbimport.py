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

import re

from indico.modules.events.models.settings import EventSetting
from indico.util.console import cformat
from indico.util.string import is_valid_mail
from indico.util.struct.iterables import committing_iterator
from indico_zodbimport import Importer, convert_to_unicode

from indico_payment_paypal.plugin import PaypalPaymentPlugin


class PaypalPaymentImporter(Importer):
    plugins = {'payment_paypal'}

    def migrate(self):
        self.migrate_event_settings()

    def migrate_event_settings(self):
        print cformat('%{white!}migrating event settings')
        default_method_name = PaypalPaymentPlugin.settings.get('method_name')
        EventSetting.delete_all(PaypalPaymentPlugin.event_settings.module)
        account_id_re = re.compile(r'^[a-zA-Z0-9]{13}$')
        for event in committing_iterator(self._iter_events(), 25):
            pp = event._modPay.payMods['PayPal']
            business = pp._business.strip()
            if not business or (not is_valid_mail(business, multi=False) and not account_id_re.match(business)):
                print cformat(' - %{yellow!}event {} skipped (business: {})').format(event.id, business or '(none)')
                continue
            PaypalPaymentPlugin.event_settings.set(event, 'enabled', True)
            method_name = convert_to_unicode(pp._title)
            if method_name.lower() == 'paypal':
                method_name = default_method_name
            PaypalPaymentPlugin.event_settings.set(event, 'method_name', method_name)
            PaypalPaymentPlugin.event_settings.set(event, 'business', pp._business)
            print cformat(' - %{cyan}event {} (business: {})').format(event.id, pp._business)

    def _iter_events(self):
        for event in self.flushing_iterator(self.zodb_root['conferences'].itervalues()):
            # Skip events where epayment is not enabled
            if not hasattr(event, '_modPay') or not event._modPay.activated:
                continue
            # Skip events where paypal is not present
            if 'PayPal' not in event._modPay.payMods:
                continue
            # Skip events where paypal is disabled
            if not event._modPay.payMods['PayPal']._enabled:
                continue
            yield event
