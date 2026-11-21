"""Audit builder tests (REQ-GOV-001)."""

import pytest

from src.governance.audit import build_audit, build_system_response
from src.schemas import CaseStatus


def test_build_audit_requires_actor_and_rule_version():
    audit = build_audit(
        actor="system",
        rule_version="rules-v1.0",
        model_version="gpt-test",
        prompt_version="prompt_v1.0",
    )
    assert audit.actor == "system"
    assert audit.rule_version == "rules-v1.0"
    assert audit.model_version == "gpt-test"
    assert audit.prompt_version == "prompt_v1.0"


def test_build_audit_rejects_empty_actor():
    with pytest.raises(ValueError):
        build_audit(actor="  ", rule_version="rules-v1.0")


def test_system_response_embeds_audit():
    audit = build_audit(actor="advisor-1", rule_version="rules-v1.0")
    resp = build_system_response(
        case_id="case-3",
        status=CaseStatus.IN_REVIEW,
        message="Routed to manual review",
        audit=audit,
    )
    assert resp.case_id == "case-3"
    assert resp.status == CaseStatus.IN_REVIEW
    assert resp.audit.actor == "advisor-1"
    assert resp.audit.rule_version == "rules-v1.0"
