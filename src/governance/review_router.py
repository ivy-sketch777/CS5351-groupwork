"""Route low-confidence / missing-doc / conflict cases to human review (REQ-GOV-002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.schemas import CaseStatus, ExtractionResult, PolicyDecision, PolicyResult

DEFAULT_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class ReviewRouteResult:
    should_review: bool
    recommended_status: CaseStatus
    reasons: list[str] = field(default_factory=list)


def _low_confidence_fields(
    extraction: Optional[ExtractionResult],
    threshold: float,
) -> list[str]:
    if extraction is None:
        return []
    low: list[str] = []
    for name in ("hospital_name", "visit_date", "rest_days", "diagnosis"):
        field_obj = getattr(extraction, name, None)
        if field_obj is None:
            continue
        if field_obj.confidence < threshold:
            low.append(f"{name}:confidence={field_obj.confidence}")
    return low


def should_route_to_review(
    *,
    extraction: Optional[ExtractionResult] = None,
    policy: Optional[PolicyDecision] = None,
    missing_docs: bool = False,
    red_flag: bool = False,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    """Return True when the case must go to manual review (REQ-GOV-002)."""
    return route_decision(
        extraction=extraction,
        policy=policy,
        missing_docs=missing_docs,
        red_flag=red_flag,
        confidence_threshold=confidence_threshold,
    ).should_review


def route_decision(
    *,
    extraction: Optional[ExtractionResult] = None,
    policy: Optional[PolicyDecision] = None,
    missing_docs: bool = False,
    red_flag: bool = False,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ReviewRouteResult:
    """Compute review routing recommendation. Never recommends APPROVED."""
    reasons: list[str] = []

    if missing_docs:
        reasons.append("missing_docs")
    if policy is not None and policy.missing_items:
        reasons.append(f"policy_missing_items:{','.join(policy.missing_items)}")

    low = _low_confidence_fields(extraction, confidence_threshold)
    if low:
        reasons.append("low_confidence:" + ";".join(low))

    if red_flag:
        reasons.append("red_flag_symptom")

    if policy is not None:
        if policy.result == PolicyResult.ROUTE_TO_REVIEW:
            reasons.append("policy:route-to-review")
        if policy.result == PolicyResult.FAIL_CLOSED:
            reasons.append("policy:fail-closed")
        if policy.is_overlapping:
            reasons.append("policy:overlapping_leave")

    if not reasons:
        # No review trigger — leave status decision to core/policy (not our write path).
        return ReviewRouteResult(
            should_review=False,
            recommended_status=CaseStatus.DRAFT,
            reasons=[],
        )

    return ReviewRouteResult(
        should_review=True,
        recommended_status=CaseStatus.IN_REVIEW,
        reasons=reasons,
    )
