"""Advisory medical-text extraction (REQ-FR-002, REQ-INV-002, REQ-INV-004)."""

import json
import logging
import math
import re
from datetime import date
from pathlib import Path
from functools import lru_cache
from typing import Any, Protocol

from src.schemas import ExtractedField, ExtractionResult

log = logging.getLogger(__name__)

# JSON syntax is a subset of YAML 1.2; no additional runtime parser needed.
@lru_cache(maxsize=1)
def _load_prompt() -> dict:
    candidates = [
        Path(__file__).resolve().parents[2] / 'prompts' / 'prompt_v1.0.yaml',
        Path.cwd() / 'prompts' / 'prompt_v1.0.yaml',
    ]
    for path in candidates:
        if path.is_file():
            content = path.read_text(encoding='utf-8').strip()
            if content:
                return json.loads(content)
    raise FileNotFoundError(f"Valid prompt_v1.0.yaml not found in: {candidates}")
PROMPT_VERSION: str = _load_prompt()['version']
FIELDS = tuple(ExtractionResult.model_fields)
MIN_CONFIDENCE = 0.75
MAX_TOTAL_TOKENS = 3000
MAX_OUTPUT_TOKENS = 300

LABELS = {
    'hospital_name': ('hospital', 'hospital name', 'clinic', 'clinic name', '醫院', '医院', '診所', '诊所'),
    'visit_date': ('visit date', 'consultation date', '就診日期', '就诊日期', '求診日期'),
    'rest_days': ('recommended rest', 'recommended rest days', '建議休息', '建议休息'),
    'diagnosis': ('diagnosis', '診斷', '诊断'),
}


class ExtractionProvider(Protocol):
    """Injected adapter: count matching full input, then generate once with an output cap."""

    def count_input_tokens(self, *, instructions: str, document: str,
                           schema: dict[str, Any]) -> int: ...

    def generate(self, *, instructions: str, document: str, schema: dict[str, Any],
                 max_output_tokens: int) -> tuple[str, int]: ...


def _wire_schema() -> dict[str, Any]:
    # Tighten the shared model for this wire path without changing its definitions.
    field = {
        'type': 'object',
        'properties': {
            'value': {'type': ['string', 'null']},
            'derived': {'type': 'boolean', 'enum': [True]},
            'confidence': {'type': 'number'},
        },
        'required': list(ExtractedField.model_fields),
        'additionalProperties': False,
    }
    return {'type': 'object', 'properties': dict.fromkeys(FIELDS, field),
            'required': list(FIELDS), 'additionalProperties': False}


def _empty() -> ExtractionResult:
    return ExtractionResult(**{key: ExtractedField(value=None, derived=True, confidence=0)
                               for key in FIELDS})


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _decode(raw: str) -> ExtractionResult:
    data = json.loads(raw, object_pairs_hook=_unique)
    if type(data) is not dict or data.keys() != set(FIELDS):
        raise ValueError('invalid field set')
    for field in data.values():
        if type(field) is not dict or field.keys() != set(ExtractedField.model_fields):
            raise ValueError('invalid derived field shape')
        confidence = field['confidence']
        value = field['value']
        if (field['derived'] is not True or (value is not None and type(value) is not str)
                or type(confidence) not in (int, float) or not 0 <= confidence <= 1
                or not math.isfinite(confidence)):
            raise ValueError('invalid derived field values')
    return ExtractionResult.model_validate(data, strict=True)


def _supported(key: str, value: str, document: str) -> bool:
    # Deliberately conservative: only one unique, complete, field-labelled value.
    labels = '|'.join(map(re.escape, LABELS[key]))
    matches = {match.strip() for match in re.findall(
        rf'(?im)^[ \t]*(?:{labels})[ \t]*[:：][ \t]*([^\r\n]*)', document)}
    if not value or value != value.strip() or matches != {value}:
        return False
    if key == 'visit_date':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
    if key == 'rest_days' and not re.fullmatch(
        r'[1-9][0-9]{0,2}(?:[ \t]*(?:days?|天|日))?', value, re.IGNORECASE
    ):
        return False
    return True


def extract(document: str, *, provider: ExtractionProvider, ai_allowed: bool = False,
            simple_request: bool = False) -> ExtractionResult:
    """Extract from sanitized, redacted text. Core sets ai_allowed only after all prechecks.

    Unknown, skipped and failed fields carry null values; this is never a policy decision.
    """
    if ai_allowed is not True or simple_request or not document.strip():
        log.info('ai extraction skipped; tokens=0')
        return _empty()

    request = {'instructions': _load_prompt()['instructions'], 'document': document,
               'schema': _wire_schema()}
    try:
        input_tokens = provider.count_input_tokens(**request)
    except Exception:
        log.warning('ai extraction preflight failed')
        return _empty()
    if (type(input_tokens) is not int or input_tokens <= 0
            or input_tokens + MAX_OUTPUT_TOKENS > MAX_TOTAL_TOKENS):
        log.info('ai extraction blocked by token budget')
        return _empty()
    try:
        raw, total = provider.generate(**request, max_output_tokens=MAX_OUTPUT_TOKENS)
    except Exception:
        log.warning('ai extraction provider failed; usage unknown')
        return _empty()
    if (type(total) is not int or total <= 0
            or total > input_tokens + MAX_OUTPUT_TOKENS):
        log.warning('ai extraction provider usage invalid')
        return _empty()
    log.info('ai extraction tokens=%d prompt=%s', total, PROMPT_VERSION)
    try:
        parsed = _decode(raw)
    except (TypeError, ValueError, RecursionError):
        log.warning('ai extraction response invalid')
        return _empty()

    confirmed = {}
    for key in FIELDS:
        field = getattr(parsed, key)
        if field.value is None or not _supported(key, field.value, document):
            field = ExtractedField(value=None, derived=True, confidence=0)
        elif field.confidence < MIN_CONFIDENCE:
            field = field.model_copy(update={'value': None})
        confirmed[key] = field
    return ExtractionResult(**confirmed)
