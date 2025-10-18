# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import Response, jsonify, stream_with_context
from flask_pluginengine import current_plugin
from webargs import fields
from webargs.flaskparser import use_kwargs

from indico.core.db import db
from indico.core.errors import IndicoError
from indico.modules.categories.controllers.base import RHManageCategoryBase
from indico.modules.events.management.controllers.base import RHManageEventBase
from indico.modules.events.notes.util import get_scheduled_notes

from indico_ai_summary.llm_interface import LLMInterface
from indico_ai_summary.models.prompt import Prompt
from indico_ai_summary.schemas import PromptSchema
from indico_ai_summary.utils import MarkupMode, chunk_text, convert_markup, generate_chunk_stream
from indico_ai_summary.views import WPCategoryManagePrompts


CATEGORY_SIDEMENU_ITEM = 'plugin_ai_summary_prompts'


class RHManageCategoryPrompts(RHManageCategoryBase):

    def _process_args(self):
        RHManageCategoryBase._process_args(self)

    def _process_GET(self):
        prompts = Prompt.query.with_parent(self.category).all()
        serialized_prompts = PromptSchema(many=True).dump(prompts)
        return WPCategoryManagePrompts.render_template('manage_category_prompts.html', category=self.category,
                                                       active_menu_item=CATEGORY_SIDEMENU_ITEM,
                                                       stored_prompts=serialized_prompts)

    @use_kwargs({'prompts': fields.List(fields.Nested(PromptSchema), required=True)}, location='json')
    def _process_POST(self, prompts):
        Prompt.query.with_parent(self.category).delete()
        for prompt_data in prompts:
            prompt = Prompt(category_id=self.category.id, name=prompt_data['name'], text=prompt_data['text'])
            db.session.add(prompt)
        return '', 204


class SummarizeEvent(RHManageEventBase):

    CSRF_ENABLED = False

    def _process_args(self):
        RHManageEventBase._process_args(self)

    @use_kwargs({'prompt': fields.Str(missing='')}, location='query')
    def _process(self, prompt):
        event = self.event
        prompt_template = prompt.strip()
        notes = get_scheduled_notes(event)
        meeting_notes = '\n\n'.join(note.html for note in notes if hasattr(note, 'html'))

        if not meeting_notes.strip():
            current_plugin.logger.error("No meeting notes found from this event's contributions.")
            return jsonify({'error': "No meeting notes found from this event's contributions."}), 400

        cleaned_text = convert_markup(meeting_notes, MarkupMode.HTML_TO_MARKDOWN)
        chunks = chunk_text(cleaned_text)
        summaries = []

        if not current_plugin.settings.get('llm_auth_token'):
            current_plugin.logger.error('LLM Auth Token is not set in plugin settings.')
            return jsonify({'error': 'LLM Auth Token is not set in plugin settings.'}), 400

        llm_model = LLMInterface(
                model_name=current_plugin.settings.get('llm_model_name'),
                host=current_plugin.settings.get('llm_host_name'),
                url=current_plugin.settings.get('llm_provider_url'),
                auth_token=current_plugin.settings.get('llm_auth_token'),
                max_tokens=current_plugin.settings.get('llm_max_tokens'),
                temperature=current_plugin.settings.get('llm_temperature'),
                system_prompt=current_plugin.settings.get('llm_system_prompt')
            )

        if current_plugin.settings.get('llm_stream_response'):
            return Response(
                stream_with_context(generate_chunk_stream(chunks, prompt_template, llm_model)),
                content_type='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'  # Disable buffering for nginx
                }
            )

        for chunk in chunks:
            full_prompt = f'{prompt_template}\n\n{chunk}'
            response = llm_model.execute(full_prompt)
            if not response:
                current_plugin.logger.error('Empty response during summarization. Check the token or model.')
                raise IndicoError('An error occurred during summarization.')

            summaries.append(response)

        combined_summary = '\n'.join(summaries)
        html_output = convert_markup(combined_summary, MarkupMode.MARKDOWN_TO_HTML)

        return {
            'summary_html': html_output
        }
