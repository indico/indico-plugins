from flask import request, jsonify
from indico_hfsummary.utils import clean_html_text, chunk_text, cern_qwen, build_prompt, convert_text_to_html_sections, markdown_to_html, html_to_markdown
import time
import os 
from indico.modules.events.controllers.base import RHEventBase
from indico.modules.events.notes.util import get_scheduled_notes


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
        #cleaned_text = clean_html_text(raw_notes)
        cleaned_text= html_to_markdown(raw_notes)
        chunks = chunk_text(cleaned_text)
        summaries = []
        token = os.getenv('CERN_SUMMARY_API_TOKEN')

        for chunk in chunks:
            # use passed prompt template
            full_prompt = f"{prompt_template.strip()}\n\n{chunk}"
            
            print(f"*********** Prompt sent to model:\n{full_prompt}")

            response = cern_qwen(full_prompt, token)
            print(f"\n*********** Response from  model:\n{response}")
            
            if response:
                summary = response['choices'][0]['message']['content']
                summaries.append(summary)
            else:
                summaries.append("[Error during summarization]")

        combined_summary = "\n".join(summaries)
        print("---------Summary ---------")
        print(combined_summary)
        html_output = markdown_to_html(combined_summary)
        print(f"[SummarizeEvent] Summarizing event {event.id}: {event.title}")
        
        print(f"Summary html output:\n{html_output}")
        
        processing_time = round(time.time() - start_time, 2)

        return jsonify({
            "summary_html": html_output,
            "processing_time": processing_time
        })
