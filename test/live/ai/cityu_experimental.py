"""Experimental Chat Completions adapter for the CityUCS/DeepSeek gateway.

Lives entirely under test/live/ai/ as an experiment. It does NOT modify
production code and does NOT claim to enforce the 3,000-total-token cap in
advance; REQ-COST-001 is NOT verified by this path. The pre-call figure is a
deliberately loose upper bound, labelled experimental, never compliance.

Implements the same ExtractionProvider protocol so the real extract() and its
ExtractionResult contract are exercised unchanged.
"""

import json
from typing import Any

from src.ai.extractor import MAX_OUTPUT_TOKENS, MAX_TOTAL_TOKENS, PROMPT, _wire_schema


class ExperimentalCityUProvider:
    """One-shot Chat Completions provider. No retries. Token cap NOT guaranteed."""

    def __init__(self, client: Any, *, model_version: str):
        self._client = client.with_options(max_retries=0, timeout=15.0)
        self.model_version = model_version
        self.observed: dict[str, Any] = {}

    JSON_SUFFIX = (
        '\n\nRespond with only a single JSON object, no prose and no code fences. '
        'It must have exactly the keys "hospital_name", "visit_date", "rest_days", '
        '"diagnosis". Each value must be an object with exactly '
        '{"value": <string or null>, "derived": true, "confidence": <number 0..1>}. '
        'Copy values verbatim from matching labelled lines; use null when absent.'
    )

    def _messages(self, instructions: str, document: str) -> list[dict[str, str]]:
        # JSON is requested via prompt only; no response_format / tool calling.
        return [{'role': 'system', 'content': instructions + self.JSON_SUFFIX},
                {'role': 'user', 'content': document}]

    def _payload(self, *, instructions: str, document: str, schema: dict[str, Any]) -> dict[str, Any]:
        return dict(
            model=self.model_version,
            messages=self._messages(instructions, document),
            temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS,
        )

    def count_input_tokens(self, *, instructions: str, document: str,
                           schema: dict[str, Any]) -> int:
        # EXPERIMENTAL loose upper bound (UTF-8 bytes of the full payload as a
        # proxy). Not a verified tokenizer count and not production compliance.
        serialized = json.dumps(self._payload(
            instructions=instructions, document=document, schema=schema),
            ensure_ascii=False, separators=(',', ':'))
        bound = len(serialized.encode('utf-8'))
        self.observed['prompt_upper_bound_bytes'] = bound
        return bound

    def generate(self, *, instructions: str, document: str, schema: dict[str, Any],
                 max_output_tokens: int) -> tuple[str, int]:
        params = self._payload(instructions=instructions, document=document, schema=schema)
        params['max_tokens'] = max_output_tokens
        result = self._client.chat.completions.create(**params)
        usage = getattr(result, 'usage', None)
        message = result.choices[0].message
        # Final answer is read ONLY from content; reasoning_content is never used.
        content = getattr(message, 'content', None) or ''
        self.observed['finish_reason'] = getattr(result.choices[0], 'finish_reason', None)
        self.observed['reasoning_present'] = bool(getattr(message, 'reasoning_content', None))
        self.observed['usage_prompt'] = getattr(usage, 'prompt_tokens', None) if usage else None
        self.observed['usage_completion'] = getattr(usage, 'completion_tokens', None) if usage else None
        self.observed['usage_total'] = getattr(usage, 'total_tokens', None) if usage else None
        # extract() requires a positive int total; if usage is absent we cannot
        # fabricate one, so report it honestly and let extract() fail closed.
        total = self.observed['usage_total']
        if type(total) is not int or total <= 0:
            raise RuntimeError('provider did not report usable usage; unknown')
        return content, total


__all__ = ['ExperimentalCityUProvider', 'MAX_OUTPUT_TOKENS', 'MAX_TOTAL_TOKENS', 'PROMPT', '_wire_schema']
