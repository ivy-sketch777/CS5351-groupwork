"""Human-review evidence packet (REQ-GOV-003, REQ-GOV-004)."""

from __future__ import annotations

from typing import Any, Optional

from src.schemas import ExtractionResult, PolicyDecision


def _derived_field_view(name: str, field_obj: Any) -> dict[str, Any]:
    """Exact derived value + derived tag for auditors (REQ-GOV-004)."""
    if field_obj is None:
        return {
            "name": name,
            "value": None,
            "derived": True,
            "confidence": None,
            "present": False,
        }
    return {
        "name": name,
        "value": field_obj.value,
        "derived": bool(field_obj.derived),
        "confidence": field_obj.confidence,
        "present": True,
    }


def build_review_packet(
    *,
    case_id: str,
    extraction: Optional[ExtractionResult] = None,
    policy: Optional[PolicyDecision] = None,
    evidence_snippets: Optional[list[str]] = None,
    review_reasons: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Build a review packet for advisors.

    Includes evidence, challenge/escalate hooks, and derived field visibility.
    Returns a plain dict (does not extend schemas.py).
    """
    derived_fields: list[dict[str, Any]] = []
    if extraction is not None:
        for name in ("hospital_name", "visit_date", "rest_days", "diagnosis"):
            derived_fields.append(_derived_field_view(name, getattr(extraction, name)))

    return {
        "case_id": case_id,
        "evidence": list(evidence_snippets or []),
        "derived_fields": derived_fields,
        "policy": None
        if policy is None
        else {
            "result": policy.result.value,
            "rule_ids_fired": list(policy.rule_ids_fired),
            "missing_items": list(policy.missing_items),
            "is_overlapping": policy.is_overlapping,
            "reason": policy.reason,
        },
        "review_reasons": list(review_reasons or []),
        # Prevent rubber-stamping (REQ-GOV-003)
        "actions": {
            "challenge_allowed": True,
            "escalate_allowed": True,
            "approve_requires_explicit_ack": True,
        },
    }
