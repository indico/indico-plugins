# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine.plugin import render_plugin_template
from wtforms.validators import DataRequired

from indico.core.plugins import IndicoPlugin
from indico.modules.events.views import WPSimpleEventDisplay
from indico.util.i18n import _
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField

from indico_ai_summary.blueprint import blueprint


class IndicoAISummarySettingsForm(IndicoForm):
    cern_summary_api_token = IndicoPasswordField(
    _('CERN Summary API Token'),
    [DataRequired()]
)


class IndicoAISummaryPlugin(IndicoPlugin):
    """AI-assisted minutes summarization tool
    Enter your CERN Summary API token. This will be used to authenticate requests to the summarization service.
    """

    configurable = True
    settings_form = IndicoAISummarySettingsForm
    default_settings = {
        'cern_summary_api_token': '',
    }

    def init(self):
        super().init()
        self.template_hook('event-manage-dropdown-notes-summarize', self.summary_button)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPSimpleEventDisplay)

    def get_blueprints(self):
        return blueprint

    def summary_button(self, event):
        return render_plugin_template('summarize_button.html', event=event)
