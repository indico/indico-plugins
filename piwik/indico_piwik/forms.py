# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from wtforms import BooleanField, IntegerField, StringField
from wtforms.validators import ValidationError

from indico.web.forms.base import IndicoForm
from indico.web.forms.widgets import SwitchWidget

from indico_piwik import _


class SettingsForm(IndicoForm):
    enabled = BooleanField(_("Track global visits"), widget=SwitchWidget())
    enabled_for_events = BooleanField(_("Track events"), widget=SwitchWidget())
    enabled_for_downloads = BooleanField(_("Track downloads"), widget=SwitchWidget())
    cache_enabled = BooleanField(_("Cache results"), widget=SwitchWidget())
    server_url = StringField(_("Piwik server URL"))
    server_api_url = StringField(_("Piwik API server URL"),
                                 description=_("Should be pointing to 'index.php'"))
    server_token = StringField(_("Piwik API token"),
                               description=_("Token to access the API. Do not share it!"))
    site_id_general = StringField(_("Global statistics ID"),
                                  description=_("Piwik site ID for global statistics"))
    site_id_events = StringField(_("Event statistics ID"),
                                 description=_("Piwik site ID for event statistics"))
    cache_ttl = IntegerField(_("Result cache TTL (seconds)"),
                             description=_("How long event reports are kept cached"))
    use_only_server_url = BooleanField(_("Use Piwik server URL for all requests"))

    def validate_site_id_events(self, field):
        if self.site_id_general is not None and field is not None and self.site_id_general.data == field.data:
            raise ValidationError(_("Event statistics can't use the same Piwik site as global statistics"))
