"""Review routing and packet tests (REQ-GOV-002/003/004)."""

from src.governance.review_packet import build_review_packet
from src.governance.review_router import route_decision, should_route_to_review
from src.schemas import (
    CaseStatus,
    ExtractedField,
    ExtractionResult,
    PolicyDecision,
    PolicyResult,
)


def _extraction(confidence: float) -> ExtractionResult:
    return ExtractionResult(
        hospital_name=ExtractedField(value="Queen Mary", derived=True, confidence=confidence),
        visit_date=ExtractedField(value="2026-11-10", derived=True, confidence=confidence),
        rest_days=ExtractedField(value="3", derived=True, confidence=confidence),
        diagnosis=ExtractedField(value="flu", derived=True, confidence=confidence),
    )


def test_low_confidence_routes_to_review():
    result = route_decision(extraction=_extraction(0.3))
    assert result.should_review is True
    assert result.recommended_status == CaseStatus.IN_REVIEW
    assert any("low_confidence" in r for r in result.reasons)


def test_high_confidence_without_other_flags_does_not_force_review():
    assert should_route_to_review(extraction=_extraction(0.95)) is False


def test_missing_docs_routes_to_review():
    result = route_decision(missing_docs=True)
    assert result.should_review is True
    assert result.recommended_status == CaseStatus.IN_REVIEW


def test_policy_route_to_review():
    policy = PolicyDecision(
        result=PolicyResult.ROUTE_TO_REVIEW,
        rule_ids_fired=["RULE-007"],
        missing_items=[],
        is_overlapping=False,
        reason=">3 days",
    )
    result = route_decision(policy=policy)
    assert result.should_review is True


def test_red_flag_routes_to_review():
    assert should_route_to_review(red_flag=True) is True


def test_router_never_recommends_approved():
    result = route_decision(missing_docs=True, red_flag=True)
    assert result.recommended_status != CaseStatus.APPROVED


def test_review_packet_shows_derived_exact_values():
    extraction = _extraction(0.9)
    packet = build_review_packet(
        case_id="case-4",
        extraction=extraction,
        evidence_snippets=["certificate page 1"],
        review_reasons=["low_confidence"],
    )
    assert packet["actions"]["challenge_allowed"] is True
    assert packet["actions"]["escalate_allowed"] is True
    names = {f["name"]: f for f in packet["derived_fields"]}
    assert names["diagnosis"]["value"] == "flu"
    assert names["diagnosis"]["derived"] is True
    assert names["visit_date"]["value"] == "2026-11-10"
