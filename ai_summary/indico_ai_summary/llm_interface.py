# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import json
from collections.abc import Generator

import httpx
import llm

from indico.core.errors import IndicoError


class LLMInterface(llm.Model):
    """Class for interacting with LLM providers.

    Uses the `llm` library to send prompts to a specified LLM provider
    and retrieve responses.

    :param model_name: The name of the LLM model to use.
    :param host: Optional host header for the request.
    :param url: The URL of the LLM provider's API endpoint.
    :param auth_token: The authentication token for accessing the LLM provider.
    :param max_tokens: The maximum number of tokens to generate in the response. Defaults to 1024.
    :param system_prompt: An optional system prompt to guide the behavior of the LLM.
    :param temperature: Sampling temperature between 0 and 1.
    """

    can_stream = False

    def __init__(self, *, model_name: str, host: str, url: str, auth_token: str, max_tokens: int = 1024,
                 temperature: float = 0.5, system_prompt: str = '') -> None:
        super().__init__()
        self.model_name = model_name
        self.host = host
        self.url = url
        self.auth_token = auth_token
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt

    def execute(self, prompt, stream=False, conversation=None) -> str | None:
        """Send a prompt to the LLM provider and retrieve the response."""
        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json',
        }

        if self.host:
            headers['Host'] = self.host

        payload = {
            'model': self.model_name,
            'messages': [
                {'role': 'system', 'content': self.system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': self.max_tokens,
            'stream': stream,
            'temperature': self.temperature,
        }

        if stream:
            return self._stream_deltas(headers, payload)

        # Non-streaming path
        try:
            response = httpx.post(self.url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except httpx.HTTPError:
            raise IndicoError('An error occurred whilst attempting to contact the LLM provider.')

    def _stream_deltas(self, headers, payload) -> Generator[str, None, None]:
        """Yield incremental content strings from a streaming response."""
        try:
            with httpx.stream('POST', self.url, headers=headers, json=payload, timeout=60) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    # OpenAI-compatible providers prefix with 'data: '
                    if line.startswith('data:'):
                        line = line.removeprefix('data:').strip()
                    if line == '[DONE]':
                        break
                    # Some providers may send keep-alives like ': ping' -> ignore non-JSON
                    if not (line.startswith('{') and line.endswith('}')):
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:  # noqa: S112
                        # Skip malformed JSON lines
                        continue
                    content, done = self._extract_content_and_done(obj)
                    if content:
                        yield content
                    if done:
                        break
        except httpx.HTTPError:
            raise IndicoError('An error occurred whilst attempting to contact the LLM provider.')

    @staticmethod
    def _extract_content_and_done(obj) -> tuple[str | None, bool]:
        """Extract content delta and completion status from a provider chunk."""
        choices = obj.get('choices') or []
        if choices:
            choice = choices[0]
            delta = choice.get('delta') or {}
            content = delta.get('content')
            if content:
                return content, False
            if choice.get('finish_reason'):
                return None, True
        # Fallback: some providers may send raw 'content'
        content = obj.get('content')
        if content:
            return content, False
        return None, False
