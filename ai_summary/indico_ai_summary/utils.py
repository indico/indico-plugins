# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools
import json
from collections.abc import Generator

from html2text import HTML2Text

from indico.modules.categories.models.categories import Category
from indico.util.string import render_markdown, sanitize_html

from indico_ai_summary.llm_interface import LLMInterface
from indico_ai_summary.models.llm_prompt import LLMPrompt


def html_to_markdown(html_string: str) -> str:
    """Convert a HTML string to Markdown.

    :param html_string: The input HTML string.
    :return: The converted Markdown string.
    """
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html_string)


def markdown_to_html(markdown_string: str) -> str:
    """Convert a Markdown string to HTML using :func:`render_markdown` from the core.

    :param markdown_string: The input Markdown string.
    :return: The converted HTML string.
    """
    return render_markdown(markdown_string)


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
                html_snapshot = sanitize_html(markdown_to_html(md_total))
                yield f"data: {json.dumps({'summary_html': html_snapshot})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Streaming error: {e}'})}\n\n"
            return
    yield 'data: [DONE]\n\n'


def get_all_prompts(category: Category) -> set[LLMPrompt]:
    """Get all prompts defined for the given event/category."""
    current_category = category or Category.get_root()
    return set(LLMPrompt.query.filter(LLMPrompt.category_id.in_(categ['id'] for categ in current_category.chain)).all())
