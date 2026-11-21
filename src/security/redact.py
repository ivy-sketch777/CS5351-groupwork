"""Privacy redaction before LLM calls (REQ-SEC-002)."""

from __future__ import annotations

import re

from src.schemas import ApplicationPayload

REDACTED = "[REDACTED]"

# CityU-style / numeric student IDs and common address cues.
_STUDENT_ID_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b[0-9]{8,10}\b"),
    re.compile(r"\b[Ss][Tt][Uu]?[-_]?[0-9]{6,10}\b"),
    re.compile(r"\b(?:student\s*(?:id|no\.?|number)|学号)\s*[:：]?\s*[A-Za-z0-9\-_]{5,}", re.IGNORECASE),
]

_ADDRESS_PATTERNS: list[re.Pattern[str]] = [
    # Stop before diagnosis / other field labels so medical text is preserved.
    re.compile(
        r"(?:地址|住址|address)\s*[:：]?\s*.+?(?=(?:\s*(?:诊断|diagnosis)\b)|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d{1,5}\s+(?:[\w\.]+\s+){0,4}(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr)\.?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Flat|Room|Unit)\s*[A-Za-z0-9\-]+[,\s]+[^\n]{5,40}",
        re.IGNORECASE,
    ),
]


def redact_pii(text: str) -> str:
    """Mask student IDs and addresses; keep medical-related wording."""
    if text is None:
        return ""
    redacted = str(text)
    for pattern in _STUDENT_ID_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    for pattern in _ADDRESS_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact_for_llm(payload: ApplicationPayload, extracted_text: str = "") -> str:
    """Build an LLM-facing payload string with PII removed (REQ-SEC-002).

    student_id is never included. Only reason + optional extracted medical text.
    """
    parts: list[str] = []
    if payload.reason_text:
        parts.append(f"reason: {redact_pii(payload.reason_text)}")
    if extracted_text:
        parts.append(f"document: {redact_pii(extracted_text)}")
    # Explicitly omit student_id, attachment paths that may encode identity, etc.
    body = "\n".join(parts)
    # Belt-and-suspenders: if student_id somehow appears in free text, scrub it.
    if payload.student_id:
        body = body.replace(payload.student_id, REDACTED)
    return body
