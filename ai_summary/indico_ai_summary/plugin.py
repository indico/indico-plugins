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
from indico.web.forms.fields import JSONField
from indico.web.forms.widgets import JinjaWidget
from indico.core.plugins.views import WPPlugins

from indico_ai_summary.blueprint import blueprint


class PromptManagerField(JSONField):
    widget = JinjaWidget('forms/prompt_manager_field_widget.html', plugin='ai_summary',
                         single_kwargs=True, single_line=True)


class PluginSettingsForm(IndicoForm):
    cern_summary_api_token = IndicoPasswordField(_('CERN Summary API Token'), [DataRequired()])
    prompts = PromptManagerField(_('Prompts'))


class IndicoAISummaryPlugin(IndicoPlugin):
    """AI-assisted minutes summarization tool
    Enter your CERN Summary API token. This will be used to authenticate requests to the summarization service.
    """

    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'cern_summary_api_token': '',
        'prompts': [],
    }

    def init(self):
        super().init()
        self.template_hook('event-manage-dropdown-notes-summarize', self.summary_button)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.js', WPPlugins)
        self.inject_bundle('main.css', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPPlugins)

    def get_blueprints(self):
        return blueprint

    def summary_button(self, event):
        return render_plugin_template('summarize_button.html', category=event.category,
                                      event=event, stored_prompts=self.settings.get('prompts'))
