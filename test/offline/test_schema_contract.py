"""Contract tests for src/schemas.py (immutable cross-module data contract)."""

from typing import Type

import pytest
from pydantic import BaseModel, ValidationError

from src.schemas import (
    ApplicationPayload,
    AuditInfo,
    CaseStatus,
    ExtractedField,
    ExtractionResult,
    PolicyDecision,
    PolicyResult,
    SystemResponse,
)


def _fields(model: Type[BaseModel]) -> set[str]:
    fields = getattr(model, "model_fields", None) or getattr(model, "__fields__", None)
    assert fields is not None, f"{model.__name__} exposes no field metadata"
    return set(fields.keys())


def _validate(model: Type[BaseModel], value: object) -> BaseModel:
    if hasattr(model, "model_validate"):
        return model.model_validate(value)
    return model.parse_obj(value)  # pragma: no cover - Pydantic v1 fallback


def test_application_payload_contract_fields_exact() -> None:
    assert _fields(ApplicationPayload) == {
        "case_id",
        "student_id",
        "course_id",
        "date_range",
        "reason_text",
        "attachment_url",
    }


def test_extraction_result_contract_fields_exact() -> None:
    assert _fields(ExtractionResult) == {
        "hospital_name",
        "visit_date",
        "rest_days",
        "diagnosis",
    }
    assert _fields(ExtractedField) == {"value", "derived", "confidence"}


def test_policy_decision_contract_fields_exact() -> None:
    assert _fields(PolicyDecision) == {
        "result",
        "rule_ids_fired",
        "missing_items",
        "is_overlapping",
        "reason",
    }


def test_policy_decision_result_enum_is_closed() -> None:
    assert {item.value for item in PolicyResult} == {
        "pass",
        "fail-closed",
        "route-to-review",
    }
    with pytest.raises(ValidationError):
        _validate(PolicyDecision, {"result": "auto-approved", "reason": "fake"})


def test_status_enum_is_closed() -> None:
    assert {item.value for item in CaseStatus} == {
        "draft",
        "pending_docs",
        "in_review",
        "approved",
        "rejected",
        "failed",
    }
    with pytest.raises(ValidationError):
        _validate(
            SystemResponse,
            {
                "case_id": "case-x",
                "status": "approved-by-ai",
                "message": "fake success",
                "audit": {"actor": "system", "rule_version": "v1.0"},
            },
        )


def test_audit_info_contract_fields_exact() -> None:
    assert _fields(AuditInfo) == {
        "actor",
        "rule_version",
        "model_version",
        "prompt_version",
    }


def test_system_response_contract_fields_exact() -> None:
    assert _fields(SystemResponse) == {"case_id", "status", "message", "audit"}


def test_extracted_field_derived_value_is_visible() -> None:
    """REQ-GOV-004: a derived value must show both its exact value and its label."""
    field = ExtractedField(value="2026-11-10", derived=True, confidence=0.9)
    assert field.value == "2026-11-10"
    assert field.derived is True
    assert 0.0 <= field.confidence <= 1.0


def test_fabricated_sick_leave_json_is_rejected_by_contract() -> None:
    """REQ-GOV-006 negative control: fake leave JSON must not pass the contract."""
    fabricated = {
        "case_id": "fake-case",
        "student_id": "2024001",
        "course_id": "COMP999",
        "date_range": {"start_date": "not-a-date", "end_date": "2026-11-03"},
        # reason_text deliberately missing; extra field tries to fake approval.
        "approved": True,
    }
    with pytest.raises(ValidationError):
        _validate(ApplicationPayload, fabricated)
