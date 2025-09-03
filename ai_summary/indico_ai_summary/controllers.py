# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import jsonify
from flask_pluginengine import current_plugin
from indico_ai_summary.views import WPCategoryManagePrompts
from webargs import fields
from webargs.flaskparser import use_kwargs

from indico.modules.events.management.controllers.base import RHManageEventBase
from indico.modules.categories.controllers.base import RHManageCategoryBase
from indico.modules.events.notes.util import get_scheduled_notes

from indico_ai_summary.utils import cern_qwen, chunk_text, html_to_markdown, markdown_to_html


CATEGORY_SIDEMENU_ITEM = 'plugin_ai_summary_prompts'


class RHManageCategoryPrompts(RHManageCategoryBase):

    def _process_args(self):
        RHManageCategoryBase._process_args(self)

    def _process_GET(self):
        return WPCategoryManagePrompts.render_template('manage_category_prompts.html', category=self.category,
                                                       active_menu_item=CATEGORY_SIDEMENU_ITEM,
                                                       stored_prompts=current_plugin.settings.get('prompts'))


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

        cleaned_text = html_to_markdown(meeting_notes)
        chunks = chunk_text(cleaned_text)
        summaries = []
        try:
            token = current_plugin.settings.get('cern_summary_api_token')
            if not token:
                current_plugin.logger.error('CERN Summary API token is not set in plugin settings.')
                return jsonify({'error': 'CERN Summary API token is not set in plugin settings.'}), 400
        except Exception as e:
            current_plugin.logger.error('Exception in cern summary api token: %s', e)

        for chunk in chunks:
            full_prompt = f'{prompt_template}\n\n{chunk}'
            try:
                response = cern_qwen(full_prompt, token)
                if response:
                    summary = response['choices'][0]['message']['content']
                    summaries.append(summary)
                else:
                    summaries.append('[Error during summarization, it might be because of the token or the model itself. Check the token again.]')  # noqa: E501
            except Exception as e:
                current_plugin.logger.error(f'Exception during summarization: {e}')
                summaries.append(f'[Exception during summarization: {e}]')

        combined_summary = '\n'.join(summaries)
        html_output = markdown_to_html(combined_summary)

        return jsonify({
            'summary_html': html_output
        })
