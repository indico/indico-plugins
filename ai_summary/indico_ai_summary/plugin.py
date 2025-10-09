# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine.plugin import render_plugin_template
from wtforms.validators import DataRequired, NumberRange

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.core.plugins.views import WPPlugins
from indico.modules.events.views import WPSimpleEventDisplay
from indico.util.i18n import _
from indico.web.flask.util import url_for
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField, JSONField
from indico.web.forms.widgets import JinjaWidget
from indico.web.menu import SideMenuItem
from wtforms.fields import StringField, URLField, IntegerField

from indico_ai_summary.blueprint import blueprint
from indico_ai_summary.controllers import CATEGORY_SIDEMENU_ITEM
from indico_ai_summary.models.prompt import Prompt
from indico_ai_summary.schemas import PromptSchema
from indico_ai_summary.views import WPCategoryManagePrompts


class PromptManagerField(JSONField):
    widget = JinjaWidget('forms/prompt_manager_field_widget.html', plugin='ai_summary',
                         single_kwargs=True, single_line=True)


class PluginSettingsForm(IndicoForm):
    llm_provider_name = StringField(_('LLM Provider Name'),
                                    [DataRequired()],
                                    description=_('The name of your LLM provider (e.g. OpenAI, Mistral etc.).'))
    llm_model_name = StringField(_('Model Name'), [DataRequired()], description=_('The name of the model '
                                 '(e.g. gpt-4o, mistral-7b-instruct-v0.1, hf-qwen25-32b etc.).'))
    llm_provider_url = URLField(_('Provider Endpoint URL'),
                                [DataRequired()],
                                description=_("The URL of the LLM provider's API endpoint. The endpoint must "
                                              "adhere to the OpenAI API specification."))
    llm_auth_token = IndicoPasswordField(_('Auth Token'),
                                         [DataRequired()],
                                         description=_('The authentication token for accessing the LLM provider.'))
    llm_host_name = StringField(_('Host Name'),
                                 description=_('An optional host header to be added to the request (if '
                                               'required by your provider).'))
    llm_max_tokens = IntegerField(_('Max Tokens'),
                                  [NumberRange(min=1)],
                                  default=1024,
                                  description=_('The maximum number of tokens to generate in the response. Defaults '
                                                'to a maximum of 1024 tokens.'))
    prompts = PromptManagerField(_('Predefined Prompts'))


class IndicoAISummaryPlugin(IndicoPlugin):
    """AI-assisted minutes summarization tool
    Configure your LLM provider as well as predefined prompts to assist in summarizing event minutes.
    """

    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'llm_model_name': None,
        'llm_provider_name': None,
        'llm_provider_url': None,
        'llm_auth_token': None,
        'llm_host_name': None,
        'llm_max_tokens': 1024,
        'prompts': [],
    }

    def init(self):
        super().init()
        self.template_hook('event-manage-dropdown-notes-summarize', self._render_summarize_button)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.js', WPPlugins)
        self.inject_bundle('main.js', WPCategoryManagePrompts)
        self.inject_bundle('main.css', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPPlugins)
        self.inject_bundle('main.css', WPCategoryManagePrompts)
        self.connect(signals.menu.items, self._extend_category_menu, sender='category-management-sidemenu')

    def get_blueprints(self):
        return blueprint

    def _render_summarize_button(self, event):
        global_prompts = self.settings.get('prompts')
        category_prompts = Prompt.query.with_parent(event.category).all()
        all_prompts = global_prompts + PromptSchema(many=True).dump(category_prompts)
        return render_plugin_template('summarize_button.html', category=event.category,
                                      event=event, stored_prompts=all_prompts)

    def _extend_category_menu(self, sender, category, **kwargs):
        return SideMenuItem(CATEGORY_SIDEMENU_ITEM, _('Prompts'),
                            url_for('plugin_ai_summary.manage_category_prompts', category),
                            icon='puzzle', weight=0)
