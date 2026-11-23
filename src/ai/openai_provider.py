"""Optional live adapter. No provider contact occurs while importing this module."""

from typing import Any


class OpenAIProvider:
    """Use a pinned structured-output-capable model and an approved API account."""

    def __init__(self, client: Any, *, model_version: str):
        self._client = client.with_options(max_retries=0, timeout=15.0)
        self.model_version = model_version

    def _request(self, *, instructions: str, document: str, schema: dict[str, Any]):
        return dict(model=self.model_version, instructions=instructions, input=document,
                    truncation='disabled', text={'format': {'type': 'json_schema',
                    'name': 'medical_extraction', 'strict': True, 'schema': schema}})

    def count_input_tokens(self, *, instructions: str, document: str,
                           schema: dict[str, Any]) -> int:
        params = self._request(instructions=instructions, document=document, schema=schema)
        return self._client.responses.input_tokens.count(**params).input_tokens

    def generate(self, *, instructions: str, document: str, schema: dict[str, Any],
                 max_output_tokens: int) -> tuple[str, int]:
        params = self._request(instructions=instructions, document=document, schema=schema)
        result = self._client.responses.create(**params, store=False,
                                               max_output_tokens=max_output_tokens)
        if result.usage is None:
            raise RuntimeError('provider did not report usage')
        # Return unsuccessful responses with empty content so their usage is still logged.
        return (result.output_text if result.status == 'completed' else '',
                result.usage.total_tokens)
