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

from wtforms import BooleanField, IntegerField, StringField

from indico.util.i18n import _
from indico.web.forms.base import IndicoForm


class SettingsForm(IndicoForm):
    enabled = BooleanField(_("Enable general statistics tracking"))
    enabled_for_events = BooleanField(_("Enable statistics tracking for events and contributions"))
    enabled_for_downloads = BooleanField(_("Enable material download tracking"))
    cache_enabled = BooleanField(_("Enable report caching"))
    cache_ttl = IntegerField(_("Report caching TTL (seconds)"))
    server_url = StringField(_("Piwik general server URL (piwik.php)"))
    server_api_url = StringField(_("Piwik API server URL (index.php)"))
    use_only_server_url = BooleanField(_("Use only the general URL for all requests"))
    server_token = StringField(_("Piwik API token"))
    site_id_general = StringField(_("Piwik site ID (general)"))
    site_id_events = StringField(_("Piwik site ID (events)"))
