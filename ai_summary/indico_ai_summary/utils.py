# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools
import json
from collections.abc import Generator
from enum import Enum

import html2text
import markdown

from indico_ai_summary.llm_interface import LLMInterface


class MarkupMode(Enum):
    """Supported markup conversion modes.

    Members
    - ``HTML_TO_MARKDOWN``: convert HTML to Markdown
    - ``MARKDOWN_TO_HTML``: convert Markdown to HTML
    """

    HTML_TO_MARKDOWN = 1
    MARKDOWN_TO_HTML = 2


def convert_markup(markup: str, mode: MarkupMode) -> str:
    """Convert markup between HTML and Markdown formats.

    :param markup: The input markup string to be converted.
    :param mode: The conversion mode. Use members of :class:`MarkupMode`,
        for example ``MarkupMode.HTML_TO_MARKDOWN`` or
        ``MarkupMode.MARKDOWN_TO_HTML``.
    :return: The converted markup string.
    """
    if mode == MarkupMode.HTML_TO_MARKDOWN:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        return h.handle(markup)
    if mode == MarkupMode.MARKDOWN_TO_HTML:
        return markdown.markdown(markup)
    raise ValueError(f'Unknown markup mode: {mode}')


def chunk_text(text: str, max_tokens: int = 1500) -> list[str]:
    """Chunk text into smaller parts based on a maximum token count.

    :param text: The input text to be chunked.
    :param max_tokens: The maximum number of tokens per chunk.
    :return: A list of text chunks.
    """
    return [' '.join(batch) for batch in itertools.batched(text.split(), max_tokens)]


def generate_chunk_stream(chunks: list[str], prompt: str, llm_model: LLMInterface) -> Generator[str, None, None]:
    """Generate a stream of chunks from the LLM model."""
    # Maintain a cumulative markdown buffer across all text chunks so snapshots grow
    md_total = ''
    for chunk in chunks:
        full_prompt = f'{prompt}\n\n{chunk}'
        response_stream = llm_model.execute(full_prompt, stream=True)
        if not response_stream:
            yield f"data: {json.dumps({'error': 'Streaming error: No response received.'})}\n\n"
            return
        try:
            for delta in response_stream:
                md_total += delta
                html_snapshot = convert_markup(md_total, MarkupMode.MARKDOWN_TO_HTML)
                yield f"data: {json.dumps({'summary_html': html_snapshot})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Streaming error: {e}'})}\n\n"
            return
    yield 'data: [DONE]\n\n'
