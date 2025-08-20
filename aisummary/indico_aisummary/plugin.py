# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine.plugin import render_plugin_template

from indico.core.plugins import IndicoPlugin
from indico.modules.events.views import WPSimpleEventDisplay

from indico_aisummary.blueprint import blueprint


class IndicoAISummaryPlugin(IndicoPlugin):
    """AI-assisted minutes summarization tool"""

    def init(self):
        super().init()
        self.template_hook('event-manage-dropdown-after-notes-compile', self.summary_button)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPSimpleEventDisplay)

    def get_blueprints(self):
        return blueprint

    def summary_button(self, event):
        return render_plugin_template('summarize_button.html', event=event)
