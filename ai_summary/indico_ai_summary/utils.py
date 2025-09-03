# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools

import html2text
import markdown
import requests
from flask_pluginengine import current_plugin


def html_to_markdown(html: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html)


def chunk_text(text: str, max_tokens: int = 1500) -> list[str]:
    return (' '.join(batch) for batch in itertools.batched(text.split(), max_tokens))


# call model hf-qwen25-32b
def cern_qwen(message_text: str, token: str):
    url = 'https://ml.cern.ch/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Host': 'hf-qwen25-32b.genai.ml.cern.ch',
    }
    data = {
        'model': 'hf-qwen25-32b',
        'messages': [{'role': 'user', 'content': message_text}],
        'max_tokens': 1024,
        'stream': False,
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.ok:
            return response.json()
        else:
            current_plugin.logger.error(
                'Error in cern_qwen: status_code=%s, response=%s', response.status_code, response.text
            )
            return None
    except Exception as e:
        current_plugin.logger.error('Exception in cern_qwen: %s', e)
        return None


def markdown_to_html(summary_text: str) -> str:
    return markdown.markdown(summary_text)
