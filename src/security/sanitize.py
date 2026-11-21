"""Input sanitization before model or policy consumption (REQ-SEC-001)."""

from __future__ import annotations

import re
from copy import deepcopy

from src.schemas import ApplicationPayload

# Phrases that attempt to override policy / force approval via the model.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
        r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|policy)",
        r"forget\s+(all\s+)?(previous|prior)\s+instructions?",
        r"you\s+are\s+now\s+(a|an|the)\s+",
        r"system\s*:\s*",
        r"<\s*/?\s*system\s*>",
        r"override\s+(the\s+)?(policy|rules?|decision)",
        r"ignore\s+(the\s+)?policy",
        r"approve\s+(this|the)\s+(leave|request|application)",
        r"must\s+approve",
        r"force\s+approve",
        r"自动批准",
        r"忽略(所有)?(之前|以上|先前)?(的)?(指令|规则|政策|提示)",
        r"无视(政策|规则|指令)",
        r"批准(这个|此|该)?(请假|申请)",
        r"强制批准",
    ]
]

_REPLACEMENT = "[FILTERED]"


def sanitize_text(text: str) -> str:
    """Neutralize prompt-injection / policy-override phrases in free text.

    Returns cleaned text safe to pass toward model or rule inputs.
    Raw attacker payloads must not survive unchanged when they match known patterns.
    """
    if text is None:
        return ""
    cleaned = str(text)
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub(_REPLACEMENT, cleaned)
    # Collapse excessive whitespace introduced by removals
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def sanitize_application(payload: ApplicationPayload) -> ApplicationPayload:
    """Return a copy of the application with reason_text sanitized (REQ-SEC-001)."""
    sanitized = deepcopy(payload)
    sanitized.reason_text = sanitize_text(payload.reason_text)
    return sanitized
