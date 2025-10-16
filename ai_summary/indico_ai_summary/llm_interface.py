import llm
import json
import httpx
from flask_pluginengine import current_plugin
from indico.core.errors import IndicoError
from collections.abc import Generator


class LLMInterface(llm.Model):
    """Class for interacting with LLM providers.

    This class uses the `llm` library to send prompts to a specified LLM provider
    and retrieve responses.

    :param model_name: The name of the LLM model to use.
    :param host: Optional host header for the request.
    :param url: The URL of the LLM provider's API endpoint.
    :param auth_token: The authentication token for accessing the LLM provider.
    :param max_tokens: The maximum number of tokens to generate in the response. Defaults to 1024.
    """

    can_stream = False

    def __init__(self, model_name: str, host: str, url: str, auth_token: str, max_tokens: int = 1024):
        super().__init__()
        self.model_name = model_name
        self.host = host
        self.url = url
        self.auth_token = auth_token
        self.max_tokens = max_tokens

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
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.max_tokens,
            'stream': stream,
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
            current_plugin.logger.error('Error during LLM request')
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
                        line = line[len('data:'):].strip()
                    if line == '[DONE]':
                        break
                    # Some providers may send keep-alives like ': ping' -> ignore non-JSON
                    if not (line.startswith('{') and line.endswith('}')):
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception as exc:
                        current_plugin.logger.error(
                            f'Failed to parse streamed JSON line: {line[:200]} ({exc})'
                        )
                        continue
                    content, done = self._extract_content_and_done(obj)
                    if content:
                        yield content
                    if done:
                        break
        except httpx.HTTPError:
            current_plugin.logger.error('Error during LLM streaming request')
            raise IndicoError('An error occurred whilst attempting to contact the LLM provider.')

    @staticmethod
    def _extract_content_and_done(obj) -> tuple[str | None, bool]:
        """Extract content delta and completion status from a provider chunk."""
        choices = obj.get('choices') or []
        if choices:
            ch0 = choices[0]
            delta = ch0.get('delta') or {}
            content = delta.get('content')
            if content:
                return content, False
            if ch0.get('finish_reason'):
                return None, True
        # Fallback: some providers may send raw 'content'
        content = obj.get('content')
        if content:
            return content, False
        return None, False


class OpenAILLMInterface(llm.Model):
    """Class for interacting with OpenAI LLM providers.

    This class extends the `LLMInterface` class to provide specific functionality
    for OpenAI LLM providers.

    :param model_name: The name of the OpenAI LLM model to use.
    :param url: The URL of the OpenAI API endpoint.
    :param auth_token: The authentication token for accessing the OpenAI API.
    :param max_tokens: The maximum number of tokens to generate in the response. Defaults to 1024.
    """

    OPENAI_ENDPOINT_URL = 'https://api.openai.com/v1/responses'

    def __init__(self, model_name: str, url: str, auth_token: str, max_tokens: int = 1024):
        super().__init__()
        self.model_name = model_name
        self.url = url
        self.auth_token = auth_token
        self.max_tokens = max_tokens

    def execute(self, prompt, stream=False, conversation=None) -> str | None:
        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json',
        }

        payload = {
            'model': self.model_name,
            'input': prompt,
            'max_output_tokens': self.max_tokens,
            'stream': stream,
        }

        try:
            response = httpx.post(self.OPENAI_ENDPOINT_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            if isinstance(data.get('output_text'), str):
                return data['output_text'].strip()

            # Sometimes the response will not be in output_text, so we need to crawl through the output array
            # for the text (JSON structure based on OpenAI API spec)
            output_items = data.get('output', [])
            for item in output_items:
                if item.get('type') == 'message':
                    for content in item.get('content', []):
                        if content.get('type') == 'output_text' and 'text' in content:
                            return content['text'].strip()

            current_plugin.logger.error('Unexpected response format from OpenAI API')
            raise IndicoError('An error occurred whilst processing the response from the OpenAI API.')

        except httpx.HTTPError:
            current_plugin.logger.error('Error during OpenAI LLM request')
            raise IndicoError('An error occurred whilst attempting to contact the OpenAI API.')


class MistralLLMInterface(llm.Model):
    """Class for interacting with Mistral LLM providers.

    This class extends the `LLMInterface` class to provide specific functionality
    for Mistral LLM providers.

    :param model_name: The name of the Mistral LLM model to use.
    :param url: The URL of the Mistral API endpoint.
    :param auth_token: The authentication token for accessing the Mistral API.
    :param max_tokens: The maximum number of tokens to generate in the response. Defaults to 1024.
    """

    MISTRAL_ENDPOINT_URL = 'https://api.mistral.ai/v1/chat/completions'

    def __init__(self, model_name: str, url: str, auth_token: str, max_tokens: int = 1024):
        super().__init__()
        self.model_name = model_name
        self.url = url
        self.auth_token = auth_token
        self.max_tokens = max_tokens

    def execute(self, prompt, stream=False, conversation=None) -> str | None:
        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json',
        }

        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.max_tokens,
            'stream': stream,
        }

        try:
            response = httpx.post(self.MISTRAL_ENDPOINT_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except httpx.HTTPError:
            current_plugin.logger.error('Error during Mistral LLM request')
            raise IndicoError('An error occurred whilst attempting to contact the Mistral API.')


class AutoLLMInterface(LLMInterface):
    """Class for automatically selecting the appropriate LLM interface based on the provider URL.

    This class extends the `LLMInterface` class and selects the appropriate subclass
    (e.g., `OpenAILLMInterface`) based on the provided URL.

    :param model_name: The name of the LLM model to use.
    :param host: Optional host header for the request.
    :param url: The URL of the LLM provider's API endpoint.
    :param auth_token: The authentication token for accessing the LLM provider.
    :param max_tokens: The maximum number of tokens to generate in the response. Defaults to 1024.
    """

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        host: str,
        url: str,
        auth_token: str,
        max_tokens: int = 1024,
    ):
        super().__init__(model_name, host, url, auth_token, max_tokens)
        self.provider_name = provider_name

    def execute(self, prompt, stream=False, conversation=None):

        # Specific handling for known providers
        if 'openai' in self.provider_name.lower():
            _openai = OpenAILLMInterface(
                model_name=self.model_name,
                url=self.url,
                auth_token=self.auth_token,
                max_tokens=self.max_tokens,
            )
            return _openai.execute(prompt, stream=stream, conversation=conversation)

        if any(x in self.provider_name.lower() for x in ['mistral', 'le chat']):
            _mistral = MistralLLMInterface(
                model_name=self.model_name,
                url=self.url,
                auth_token=self.auth_token,
                max_tokens=self.max_tokens,
            )
            return _mistral.execute(prompt, stream=stream, conversation=conversation)

        return super().execute(prompt, stream=stream, conversation=conversation)
