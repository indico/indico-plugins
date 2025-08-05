from flask import request, jsonify
from indico_hfsummary.utils import clean_html_text, chunk_text, cern_qwen, build_prompt, convert_text_to_html_sections
import time
import os 
from indico.web.rh import RH
from indico.modules.events.controllers.base import RHEventBase
from indico.modules.events.notes.util import get_scheduled_notes


# send a text to summarize
class Summarizer(RH):
    CSRF_ENABLED = False # disable the protection for external api posts(postman)

    def _process_POST(self):
        start_time = time.time()
        data = request.get_json()
        raw_html = data.get('message_text')
        token = data.get('token')

        if not raw_html or not token:
            return jsonify({"error": "Both message_text and token are required"}), 400

        cleaned_text = clean_html_text(raw_html)
        chunks = chunk_text(cleaned_text)
        summaries = []

        for chunk in chunks:
            prompt = build_prompt(chunk)
            print(prompt)

            response = cern_qwen(prompt, token)
            print(response)

            if response:
                summary = response['choices'][0]['message']['content']
                summaries.append(summary)
            else:
                summaries.append("[Error during summarization]")

        combined_summary = "\n".join(summaries)
        html_output = convert_text_to_html_sections(combined_summary)
        processing_time = round(time.time() - start_time, 2)

        return f"""
        <html>
        <head><title>Meeting Minutes Summary</title></head>
        <body>
        <h2>Meeting Minutes Summary</h2>
        {''.join(html_output)}
        <p><i>Processing Time: {processing_time} seconds</i></p>
        </body>
        </html>
        """


        '''

        return jsonify({
                    "summary_html": html_output,
                    "processing_time": processing_time
                })

        '''
        
#---------------------------------------------------------------------------------------------------------------
# summarize the event
class SummarizeEvent(RHEventBase):

    CSRF_ENABLED = False

    def _process_args(self):
        print(request.view_args)
        RHEventBase._process_args(self)

    def _process(self):
        event = self.event
        prompt_template = request.args.get('prompt', '').strip()

        notes = get_scheduled_notes(self.event)
        contrib_notes_html = "\n\n".join(note.html for note in notes if hasattr(note, 'html'))
        raw_notes = contrib_notes_html

        if not raw_notes.strip():
            return jsonify({"error": "No meeting notes found for this event or its contributions."}), 400

        start_time = time.time()
        cleaned_text = clean_html_text(raw_notes)
        chunks = chunk_text(cleaned_text)
        summaries = []
        token = os.getenv('CERN_SUMMARY_API_TOKEN')

        for chunk in chunks:
            # Use passed prompt template
            full_prompt = f"{prompt_template.strip()}\n\n{chunk}"
            
            print(f"[DEBUG] Prompt sent to model:\n{full_prompt}")

            response = cern_qwen(full_prompt, token)
            
            if response:
                summary = response['choices'][0]['message']['content']
                summaries.append(summary)
            else:
                summaries.append("[Error during summarization]")

        combined_summary = "\n".join(summaries)
        print(combined_summary)
        html_output = convert_text_to_html_sections(combined_summary)
        print(f"[SummarizeEvent] Summarizing event {event.id}: {event.title}")
        
        #print(f"Summary:\n{html_output}")
        
        processing_time = round(time.time() - start_time, 2)

        return jsonify({
            "summary_html": html_output,
            "processing_time": processing_time
        })
