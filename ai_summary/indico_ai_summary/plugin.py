# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask_pluginengine.plugin import render_plugin_template
from wtforms.fields import BooleanField, FloatField, IntegerField, StringField, TextAreaField, URLField
from wtforms.validators import DataRequired, NumberRange
from wtforms.widgets import NumberInput

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.core.plugins.views import WPPlugins
from indico.modules.events.views import WPSimpleEventDisplay
from indico.util.i18n import _
from indico.web.flask.util import url_for
from indico.web.forms.base import IndicoForm
from indico.web.forms.fields import IndicoPasswordField, JSONField
from indico.web.forms.widgets import JinjaWidget, SwitchWidget
from indico.web.menu import SideMenuItem

from indico_ai_summary.blueprint import blueprint
from indico_ai_summary.controllers import CATEGORY_SIDEMENU_ITEM
from indico_ai_summary.views import WPCategoryManagePrompts


class PromptManagerField(JSONField):
    widget = JinjaWidget('forms/prompt_manager_field_widget.html', plugin='ai_summary',
                         single_kwargs=True, single_line=True)


class PluginSettingsForm(IndicoForm):
    llm_provider_name = StringField(_('LLM Provider Name'),
                                    [DataRequired()],
                                    description=_('The name of your LLM provider (e.g. OpenAI, Mistral etc.).'))
    llm_model_name = StringField(_('Model Name'), [DataRequired()], description=_('The name of the model '
                                 '(e.g. gpt-4o, mistral-large-latest, hf-qwen25-32b etc.).'))
    llm_provider_url = URLField(_('Provider Endpoint URL'),
                                [DataRequired()],
                                description=_("The URL of the LLM provider's API endpoint. The endpoint must "
                                              "adhere to the OpenAI API specification."))
    llm_auth_token = IndicoPasswordField(_('Auth Token'),
                                         [DataRequired()],
                                         toggle=True,
                                         description=_('The authentication token for accessing the LLM provider.'))
    llm_host_header = StringField(_('Host Name'),
                                 description=_('An optional host header to be added to the request (if '
                                               'required by your provider).'))
    llm_max_tokens = IntegerField(_('Max Tokens'),
                                  [NumberRange(min=1)],
                                  description=_('The maximum number of tokens to generate in the response. Defaults '
                                                'to a maximum of 1024 tokens.'))
    llm_temperature = FloatField(_('Temperature'),
                                   [NumberRange(min=0, max=1)],
                                   widget=NumberInput(step='0.1'),
                                   description=_('The sampling temperature to use, between 0 and 1. Higher values '
                                                 'like 0.8 will make the response more random, while lower values like '
                                                 '0.2 will make it more focused and deterministic.'))
    llm_system_prompt = TextAreaField(_('System Prompt'),
                                    description=_('An optional system prompt to guide the behavior of the LLM. '
                                                  'This prompt will be prepended to all user prompts.'))
    llm_stream_response = BooleanField(_('Stream Response'),
                                        widget=SwitchWidget(),
                                        default=False,
                                        description=_('Stream back the live token-by-token response from the LLM.'))
    display_info = BooleanField(_('Display LLM Info'), widget=SwitchWidget(), default=True,
                                 description=_('Display the model name and LLM provider name in the summarizer modal.'))
    prompts = PromptManagerField(_('Predefined Prompts'))


class IndicoAISummaryPlugin(IndicoPlugin):
    """AI-assisted minutes summarization tool

    Configure your LLM provider as well as predefined prompts to assist in summarizing meeting minutes.
    """

    configurable = True
    settings_form = PluginSettingsForm
    default_settings = {
        'llm_model_name': None,
        'llm_provider_name': None,
        'llm_provider_url': None,
        'llm_auth_token': None,
        'llm_host_header': None,
        'llm_max_tokens': 1024,
        'llm_temperature': 0.5,
        'llm_system_prompt': '',
        'llm_stream_response': False,
        'display_info': True,
        'prompts': [],
    }

    def init(self):
        super().init()
        self.template_hook('manage-button-after-notes_compile', self._render_summarize_button)
        self.inject_bundle('main.js', WPSimpleEventDisplay)
        self.inject_bundle('main.js', WPPlugins)
        self.inject_bundle('main.js', WPCategoryManagePrompts)
        self.inject_bundle('main.css', WPSimpleEventDisplay)
        self.inject_bundle('main.css', WPPlugins)
        self.inject_bundle('main.css', WPCategoryManagePrompts)
        self.connect(signals.menu.items, self._extend_category_menu, sender='category-management-sidemenu')

    def get_blueprints(self):
        return blueprint

    def _render_summarize_button(self, item, item_type):
        stream_response = self.settings.get('llm_stream_response')
        show_info = self.settings.get('display_info')
        event = item

        llm_info = None
        if show_info:
            llm_info = {
                'provider_name': self.settings.get('llm_provider_name'),
                'model_name': self.settings.get('llm_model_name')
            }

        return render_plugin_template('summarize_button.html',
                                      item=item,
                                      item_type=item_type,
                                      category=event.category,
                                      event=event,
                                      stream_response=stream_response,
                                      llm_info=llm_info)

    def _extend_category_menu(self, sender, category, **kwargs):
        return SideMenuItem(CATEGORY_SIDEMENU_ITEM, _('Prompts'),
                            url_for('plugin_ai_summary.manage_category_prompts', category),
                            icon='puzzle', weight=0)
