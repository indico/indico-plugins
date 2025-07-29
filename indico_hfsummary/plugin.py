from indico.core.plugins import IndicoPlugin
from indico_hfsummary.blueprint import blueprint
from flask import request, jsonify
import time
from indico_hfsummary.utils import clean_html_text, chunk_text, cern_qwen, build_prompt, convert_text_to_html_sections



class IndicoHFSummaryPlugin(IndicoPlugin):
    def init(self):
        super().init()


    
    def get_blueprints(self):
        return None
   

    # summarization logic 
    def summarize():
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
            response = cern_qwen(prompt, token)
            if response:
                summary = response['choices'][0]['message']['content']
                summaries.append(summary)
            else:
                summaries.append("[Error during summarization]")

        combined_summary = "\n".join(summaries)
        html_output = convert_text_to_html_sections(combined_summary)
        processing_time = round(time.time() - start_time, 2)

        return jsonify({
            "summary_html": html_output,
            "processing_time": processing_time
        })



