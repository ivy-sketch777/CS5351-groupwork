from datetime import date

import pytest

from src.policy import engine
from src.policy.engine import evaluate_policy
from src.schemas import ApplicationPayload, DateRange, PolicyResult


def _payload(start: date, end: date, attachment_url=None) -> ApplicationPayload:
    return ApplicationPayload(
        case_id="case-001",
        student_id="student-001",
        course_id="COMP999",
        date_range=DateRange(start_date=start, end_date=end),
        reason_text="flu",
        attachment_url=attachment_url,
    )


def _three_days():
    return _payload(date(2026, 11, 1), date(2026, 11, 3))


def test_three_days_matches_no_rule_and_defaults_fail_closed():
    decision = evaluate_policy(_three_days())

    assert decision.result is PolicyResult.FAIL_CLOSED
    assert decision.rule_ids_fired == []
    assert decision.reason == "No policy rule matched; defaulting to fail-closed."


def test_overlap_hits_overlap_rule_and_fails_closed():
    payload = _payload(date(2026, 11, 1), date(2026, 11, 5))

    decision = evaluate_policy(payload, overlap_flag=True)

    assert decision.result is PolicyResult.FAIL_CLOSED
    assert decision.rule_ids_fired[0] == "RULE-INV-003-OVERLAP"
    assert decision.is_overlapping is True


def test_five_days_without_overlap_routes_to_review():
    payload = _payload(date(2026, 11, 1), date(2026, 11, 4))

    decision = evaluate_policy(payload)

    assert decision.result is PolicyResult.ROUTE_TO_REVIEW
    assert decision.rule_ids_fired == ["RULE-FR-007-LONG-LEAVE"]


def test_ten_days_without_evidence_fails_closed_with_missing_item():
    payload = _payload(date(2026, 11, 1), date(2026, 11, 10))

    decision = evaluate_policy(payload)

    assert decision.result is PolicyResult.FAIL_CLOSED
    assert "RULE-FR-003-EVIDENCE-REQUIRED" in decision.rule_ids_fired
    assert decision.missing_items == ["medical_certificate"]


def test_one_day_hits_short_leave_and_passes():
    payload = _payload(date(2026, 11, 1), date(2026, 11, 1))

    decision = evaluate_policy(payload)

    assert decision.result is PolicyResult.PASS
    assert decision.rule_ids_fired == ["RULE-FR-003-SHORT-LEAVE"]


def test_invalid_date_fails_closed():
    payload = _payload(date(2026, 11, 5), date(2026, 11, 1))

    decision = evaluate_policy(payload)

    assert decision.result is PolicyResult.FAIL_CLOSED
    assert "RULE-INV-001-INVALID-DATE" in decision.rule_ids_fired


def test_loader_failure_returns_fail_closed(monkeypatch):
    def _boom(path):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(engine, "load_rules", _boom)

    decision = evaluate_policy(_three_days())

    assert decision.result is PolicyResult.FAIL_CLOSED
    assert decision.rule_ids_fired == []
    assert "Policy evaluation failed" in decision.reason or (
        "Unexpected policy evaluation error" in decision.reason
    )


def test_condition_eval_failure_returns_fail_closed(monkeypatch):
    def _boom(expr, context):
        raise ValueError("bad condition")

    monkeypatch.setattr(engine, "evaluate_condition", _boom)

    decision = evaluate_policy(_three_days())

    assert decision.result is PolicyResult.FAIL_CLOSED
    assert decision.rule_ids_fired == []


def test_determinism_across_one_hundred_runs():
    payload = _payload(date(2026, 11, 1), date(2026, 11, 4))

    results = [evaluate_policy(payload) for _ in range(100)]
    snapshots = {
        (r.result, tuple(r.rule_ids_fired), tuple(r.missing_items), r.is_overlapping, r.reason)
        for r in results
    }

    assert len(snapshots) == 1
    assert all(r.result is PolicyResult.ROUTE_TO_REVIEW for r in results)


def test_decision_is_always_fully_populated():
    for payload in (
        _three_days(),
        _payload(date(2026, 11, 1), date(2026, 11, 5), attachment_url="http://x/cert.pdf"),
    ):
        decision = evaluate_policy(payload)
        assert isinstance(decision.result, PolicyResult)
        assert isinstance(decision.rule_ids_fired, list)
        assert isinstance(decision.missing_items, list)
        assert isinstance(decision.is_overlapping, bool)
        assert isinstance(decision.reason, str) and decision.reason
