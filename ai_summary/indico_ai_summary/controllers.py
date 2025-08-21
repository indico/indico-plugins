# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import os
import time

from flask import jsonify, request
from webargs import fields
from webargs.flaskparser import use_kwargs

from indico.modules.events.notes.controllers import RHManageNoteBase
from indico.modules.events.notes.util import get_scheduled_notes

from indico_ai_summary.utils import cern_qwen, chunk_text, html_to_markdown, markdown_to_html


class SummarizeEvent(RHManageNoteBase):

    CSRF_ENABLED = False

    def _process_args(self):
        print(request.view_args)
        RHManageNoteBase._process_args(self)

    @use_kwargs({'prompt': fields.Str(missing='')})
    def _process(self, prompt):
        event = self.event
        prompt_template = prompt.strip()

        notes = get_scheduled_notes(event)
        meeting_notes = '\n\n'.join(note.html for note in notes if hasattr(note, 'html'))

        if not meeting_notes.strip():
            return jsonify({'error': "No meeting notes found from this event's contributions."}), 400

        start_time = time.time()
        cleaned_text = html_to_markdown(meeting_notes)
        chunks = chunk_text(cleaned_text)
        summaries = []
        token = self.plugin.settings.get('cern_summary_api_token')
        if not token:
            return jsonify({'error': 'CERN Summary API token is not set in plugin settings.'}), 400

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

        processing_time = round(time.time() - start_time, 2)

        return jsonify({
            'summary_html': html_output,
            'processing_time': processing_time
        })
