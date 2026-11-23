"""System integration tests using mocked policy (AGENTS.md: Mock 优先)."""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.core.api import MOCK_COUNSELOR_TOKEN, app  # noqa: E402
from src.core.database import Base, get_db  # noqa: E402
from src.core.mock_policy import evaluate_policy  # noqa: E402
from src.schemas import ApplicationPayload, CaseStatus, SystemResponse  # noqa: E402

AUTH_HEADER = {"X-Counselor-Token": MOCK_COUNSELOR_TOKEN}

LONG_PAYLOAD = {
    "case_id": "integrate-long-001",
    "student_id": "2024100",
    "course_id": "COMP555",
    "date_range": {"start_date": "2026-12-01", "end_date": "2026-12-05"},
    "reason_text": "连续五天发烧需休息",
    "attachment_url": "https://example.com/long.pdf",
}

SHORT_PAYLOAD = {
    "case_id": "integrate-short-001",
    "student_id": "2024101",
    "course_id": "COMP556",
    "date_range": {"start_date": "2026-12-08", "end_date": "2026-12-09"},
    "reason_text": "轻微感冒",
    "attachment_url": None,
}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _assert_system_response(payload: dict, expected_status: CaseStatus) -> SystemResponse:
    response = SystemResponse.model_validate(payload)
    assert response.status is expected_status
    return response


def test_full_review_chain_never_fakes_success(client: TestClient) -> None:
    """REQ-FR-004/REQ-INV-001: approved only after an authenticated manual review."""
    applied = client.post("/api/apply", json=LONG_PAYLOAD)
    assert applied.status_code == 200
    _assert_system_response(applied.json(), CaseStatus.IN_REVIEW)

    status = client.get(f"/api/status/{LONG_PAYLOAD['case_id']}")
    _assert_system_response(status.json(), CaseStatus.IN_REVIEW)

    reviewed = client.post(
        f"/api/review/{LONG_PAYLOAD['case_id']}/decision",
        json={"decision": "approve", "reason": "材料齐全，人工复核通过"},
        headers=AUTH_HEADER,
    )
    assert reviewed.status_code == 200
    approved = _assert_system_response(reviewed.json(), CaseStatus.APPROVED)
    assert approved.audit.actor == MOCK_COUNSELOR_TOKEN

    final = client.get(f"/api/status/{LONG_PAYLOAD['case_id']}")
    _assert_system_response(final.json(), CaseStatus.APPROVED)


def test_supplement_reenters_review_queue(client: TestClient) -> None:
    """REQ-FR-005: missing documents lead to guidance, then re-review."""
    applied = client.post("/api/apply", json=SHORT_PAYLOAD)
    _assert_system_response(applied.json(), CaseStatus.PENDING_DOCS)

    supplemented = client.post(
        f"/api/apply/{SHORT_PAYLOAD['case_id']}/supplement",
        json={"additional_text": "已补交医疗证明", "attachment_url": "https://example.com/new.pdf"},
    )
    assert supplemented.status_code == 200
    _assert_system_response(supplemented.json(), CaseStatus.IN_REVIEW)

    pending = client.get("/api/review/pending", headers=AUTH_HEADER)
    assert SHORT_PAYLOAD["case_id"] in {item["case_id"] for item in pending.json()}


def test_unauthenticated_decision_does_not_fake_success(client: TestClient) -> None:
    """REQ-ARCH-001: no write path to approved without the authorized reviewer."""
    client.post("/api/apply", json=LONG_PAYLOAD)
    denied = client.post(
        f"/api/review/{LONG_PAYLOAD['case_id']}/decision",
        json={"decision": "approve", "reason": "伪造授权"},
    )
    assert denied.status_code == 401

    status = client.get(f"/api/status/{LONG_PAYLOAD['case_id']}")
    _assert_system_response(status.json(), CaseStatus.IN_REVIEW)


def test_same_input_same_outcome_class() -> None:
    """REQ-INV-005: deterministic policy mock must be repeatable."""
    payload = ApplicationPayload.model_validate(LONG_PAYLOAD)
    first = evaluate_policy(payload).model_dump()
    second = evaluate_policy(payload).model_dump()
    assert first == second
    assert first["result"] == "route-to-review"
    assert first["rule_ids_fired"], "A deterministic decision must cite its Rule ID"


def test_root_contains_no_hardcoded_approved_shortcut(client: TestClient) -> None:
    """REQ-INV-001: short leave never becomes approved without review."""
    applied = client.post("/api/apply", json=SHORT_PAYLOAD)
    _assert_system_response(applied.json(), CaseStatus.PENDING_DOCS)

    status = client.get(f"/api/status/{SHORT_PAYLOAD['case_id']}")
    _assert_system_response(status.json(), CaseStatus.PENDING_DOCS)
