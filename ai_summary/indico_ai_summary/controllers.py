# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from flask import jsonify, request
from flask_pluginengine import current_plugin
from webargs import fields
from webargs.flaskparser import use_kwargs

from indico.modules.events.management.controllers.base import RHManageEventBase
from indico.modules.events.notes.util import get_scheduled_notes

from indico_ai_summary.utils import cern_qwen, chunk_text, html_to_markdown, markdown_to_html


class SummarizeEvent(RHManageEventBase):

    CSRF_ENABLED = False

    def _process_args(self):
        print(request.view_args)
        RHManageEventBase._process_args(self)

    @use_kwargs({'prompt': fields.Str(missing='')})
    def _process(self, prompt):
        event = self.event
        prompt_template = prompt.strip()

        notes = get_scheduled_notes(event)
        meeting_notes = '\n\n'.join(note.html for note in notes if hasattr(note, 'html'))

        if not meeting_notes.strip():
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
            full_prompt = f'{prompt_template.strip()}\n\n{chunk}'
            try:
                response = cern_qwen(full_prompt, token)
                if response:
                    summary = response['choices'][0]['message']['content']
                    summaries.append(summary)
                else:
                    summaries.append('[Error during summarization]')
            except Exception as e:
                summaries.append(f'[Exception during summarization: {e}]')

        combined_summary = '\n'.join(summaries)
        html_output = markdown_to_html(combined_summary)
        print(f'Summary html output:\n{html_output}')

        return jsonify({
            'summary_html': html_output
        })
