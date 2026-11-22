"""CityUCS/DeepSeek Chat Completions adapter (INCOMPLETE integration).

This adapter lets ``extract()`` talk to the school's LiteLLM gateway at
``https://llm.cs.cityu.edu.hk/v1`` using Chat Completions. Two facts about that
deployment shape the design and its limitations:

* ``response_format=json_schema`` is rejected (HTTP 400), so JSON output is
  requested through the prompt only and validated strictly locally.
* No defensible pre-generation token count is available: the LiteLLM count
  routes (``/responses/input_tokens`` and the SDK's ``/count``) both returned
  HTTP 405, and no verified tokenizer plus Chat Completions framing exists for
  this alias. There is therefore no way to enforce the 3,000-total-token cap
  before a call.

Consequently ``count_input_tokens`` fails closed with ``TokenBudgetUnavailable``
and, through ``extract()``, generation stays blocked. This is an INCOMPLETE
integration: REQ-COST-001 is NOT satisfied by the production path. It is not a
working production feature until a supported counting method (or documented
tokenizer + framing) is available. No byte-length, character-ratio, or arbitrary
overhead estimate is used as a token count.

The answer is read only from ``message.content``; ``reasoning_content`` is never
used as the extraction answer.
"""

import logging
from typing import Any

log = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 300
TIMEOUT_SECONDS = 30.0

JSON_SUFFIX = (
    '\n\nRespond with only a single JSON object, no prose and no code fences. '
    'It must have exactly the keys "hospital_name", "visit_date", "rest_days", '
    '"diagnosis". Each value must be an object with exactly '
    '{"value": <string or null>, "derived": true, "confidence": <number 0..1>}. '
    'Copy values verbatim from matching labelled lines; use null when absent.'
)


class TokenBudgetUnavailable(RuntimeError):
    """Raised when no defensible pre-generation token count can be produced."""


class CityUProvider:
    """One-shot Chat Completions provider. Generation is blocked at preflight.

    Implements the same ``ExtractionProvider`` protocol as ``OpenAIProvider``.
    ``generate`` is fully functional but is unreachable through ``extract()``
    while counting is unavailable, because ``count_input_tokens`` fails closed.
    """

    def __init__(self, client: Any, *, model_version: str):
        self._client = client.with_options(max_retries=0, timeout=TIMEOUT_SECONDS)
        self.model_version = model_version
        # Per-call usage metadata; reset at the start of every generate() so a
        # failed request can never surface a previous call's usage.
        self.last_usage: dict[str, Any] | None = None

    def _messages(self, instructions: str, document: str) -> list[dict[str, str]]:
        # JSON requested via prompt only; no response_format and no tool calling.
        return [{'role': 'system', 'content': instructions + JSON_SUFFIX},
                {'role': 'user', 'content': document}]

    def _payload(self, *, instructions: str, document: str,
                 max_output_tokens: int) -> dict[str, Any]:
        return dict(
            model=self.model_version,
            messages=self._messages(instructions, document),
            temperature=0,
            max_tokens=max_output_tokens,
        )

    def count_input_tokens(self, *, instructions: str, document: str,
                           schema: dict[str, Any]) -> int:
        raise TokenBudgetUnavailable(
            'CityU pre-generation token counting is unavailable (LiteLLM count '
            'routes returned 405; no verified tokenizer/framing). The 3,000-token '
            'cap cannot be enforced before the call, so generation is blocked. '
            'REQ-COST-001 is NOT satisfied by this path.')

    def generate(self, *, instructions: str, document: str, schema: dict[str, Any],
                 max_output_tokens: int) -> tuple[str, int]:
        # Reset usage first so a failure below cannot expose earlier metadata.
        self.last_usage = None
        params = self._payload(instructions=instructions, document=document,
                               max_output_tokens=max_output_tokens)
        result = self._client.chat.completions.create(**params)

        choice = result.choices[0]
        message = choice.message
        finish_reason = getattr(choice, 'finish_reason', None)
        usage = getattr(result, 'usage', None)
        usage_prompt = getattr(usage, 'prompt_tokens', None) if usage else None
        usage_completion = getattr(usage, 'completion_tokens', None) if usage else None
        usage_total = getattr(usage, 'total_tokens', None) if usage else None
        # Presence flag for audit only; reasoning_content is never the answer.
        reasoning_present = bool(getattr(message, 'reasoning_content', None))

        # Reject truncated output even if the partial text happens to parse.
        if finish_reason == 'length':
            self.last_usage = {
                'finish_reason': finish_reason,
                'reasoning_present': reasoning_present,
                'prompt_tokens': usage_prompt,
                'completion_tokens': usage_completion,
                'total_tokens': usage_total,
                'rejected': 'truncated',
            }
            log.warning('ai extraction response truncated; rejected')
            raise RuntimeError('provider output truncated (finish_reason=length)')

        if type(usage_total) is not int or usage_total <= 0:
            self.last_usage = {'finish_reason': finish_reason,
                               'reasoning_present': reasoning_present,
                               'rejected': 'usage unknown'}
            raise RuntimeError('provider did not report usable usage; unknown')

        # Answer from content only; reasoning_content is ignored.
        content = getattr(message, 'content', None) or ''
        self.last_usage = {
            'finish_reason': finish_reason,
            'reasoning_present': reasoning_present,
            'prompt_tokens': usage_prompt,
            'completion_tokens': usage_completion,
            'total_tokens': usage_total,
        }
        return content, usage_total


__all__ = ['CityUProvider', 'TokenBudgetUnavailable', 'MAX_OUTPUT_TOKENS']
