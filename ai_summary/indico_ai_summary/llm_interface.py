import llm
import httpx
from flask_pluginengine import current_plugin
from indico.core.errors import IndicoError


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

        try:
            response = httpx.post(self.url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except httpx.HTTPError:
            current_plugin.logger.error('Error during LLM request')
            raise IndicoError('An error occurred whilst attempting to contact the LLM provider.')
