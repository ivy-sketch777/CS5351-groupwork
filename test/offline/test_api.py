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

VALID_PAYLOAD = {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "student_id": "2024001",
    "course_id": "COMP999",
    "date_range": {"start_date": "2026-11-01", "end_date": "2026-11-03"},
    "reason_text": "感冒发烧，需要休息",
    "attachment_url": "https://example.com/medical.pdf",
}

LONG_PAYLOAD = {
    "case_id": "22222222-2222-2222-2222-222222222222",
    "student_id": "2024002",
    "course_id": "COMP888",
    "date_range": {"start_date": "2026-11-01", "end_date": "2026-11-05"},
    "reason_text": "手术后需要休息五天",
    "attachment_url": "https://example.com/medical2.pdf",
}

SHORT_PAYLOAD = {
    "case_id": "33333333-3333-3333-3333-333333333333",
    "student_id": "2024003",
    "course_id": "COMP777",
    "date_range": {"start_date": "2026-11-10", "end_date": "2026-11-11"},
    "reason_text": "轻微感冒",
    "attachment_url": None,
}

AUTH_HEADER = {"X-Counselor-Token": MOCK_COUNSELOR_TOKEN}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
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


def test_apply_persists_and_returns_pending_docs(client):
    resp = client.post("/api/apply", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == VALID_PAYLOAD["case_id"]
    assert body["status"] == "pending_docs"
    assert body["message"] == "申请已受理，正在等待材料提取"
    assert body["audit"]["actor"] == "system"
    assert body["audit"]["rule_version"] == "v1.0"


def test_short_leave_flows_to_pending_docs(client):
    resp = client.post("/api/apply", json=SHORT_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_docs"

    status_resp = client.get(f"/api/status/{SHORT_PAYLOAD['case_id']}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending_docs"


def test_long_leave_flows_to_in_review(client):
    resp = client.post("/api/apply", json=LONG_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_review"
    assert resp.json()["message"] == "申请已受理，正在人工复核"

    status_resp = client.get(f"/api/status/{LONG_PAYLOAD['case_id']}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "in_review"


def test_review_pending_requires_auth(client):
    resp = client.get("/api/review/pending")
    assert resp.status_code == 401


def test_review_pending_returns_only_in_review(client):
    client.post("/api/apply", json=LONG_PAYLOAD)
    client.post("/api/apply", json=SHORT_PAYLOAD)

    resp = client.get("/api/review/pending", headers=AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    case_ids = {item["case_id"] for item in body}
    assert LONG_PAYLOAD["case_id"] in case_ids
    assert SHORT_PAYLOAD["case_id"] not in case_ids
    assert all(item["status"] == "in_review" for item in body)


def test_status_unknown_case_returns_404(client):
    resp = client.get("/api/status/non-existent-case")
    assert resp.status_code == 404


def test_duplicate_case_id_returns_409(client):
    client.post("/api/apply", json=VALID_PAYLOAD)
    resp = client.post("/api/apply", json=VALID_PAYLOAD)
    assert resp.status_code == 409


def test_apply_missing_required_field_returns_422(client):
    bad = dict(VALID_PAYLOAD)
    del bad["student_id"]
    resp = client.post("/api/apply", json=bad)
    assert resp.status_code == 422


def test_apply_without_attachment_succeeds(client):
    no_attach = dict(VALID_PAYLOAD)
    no_attach.pop("attachment_url", None)
    resp = client.post("/api/apply", json=no_attach)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_docs"


def test_review_approve_long_case(client):
    client.post("/api/apply", json=LONG_PAYLOAD)
    resp = client.post(
        f"/api/review/{LONG_PAYLOAD['case_id']}/decision",
        json={"decision": "approve", "reason": "材料齐全，同意请假"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["audit"]["actor"] == MOCK_COUNSELOR_TOKEN

    status_resp = client.get(f"/api/status/{LONG_PAYLOAD['case_id']}")
    assert status_resp.json()["status"] == "approved"


def test_review_reject_long_case(client):
    client.post("/api/apply", json=LONG_PAYLOAD)
    resp = client.post(
        f"/api/review/{LONG_PAYLOAD['case_id']}/decision",
        json={"decision": "reject", "reason": "证明材料不足"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    status_resp = client.get(f"/api/status/{LONG_PAYLOAD['case_id']}")
    assert status_resp.json()["status"] == "rejected"


def test_review_on_non_in_review_returns_400(client):
    client.post("/api/apply", json=SHORT_PAYLOAD)
    resp = client.post(
        f"/api/review/{SHORT_PAYLOAD['case_id']}/decision",
        json={"decision": "approve", "reason": "随意批准"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_review_unknown_case_returns_404(client):
    resp = client.post(
        "/api/review/does-not-exist/decision",
        json={"decision": "approve", "reason": "无"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 404


def test_review_requires_auth(client):
    client.post("/api/apply", json=LONG_PAYLOAD)
    resp = client.post(
        f"/api/review/{LONG_PAYLOAD['case_id']}/decision",
        json={"decision": "approve", "reason": "无 token"},
    )
    assert resp.status_code == 401


def test_supplement_pending_docs_reenters_queue(client):
    client.post("/api/apply", json=SHORT_PAYLOAD)
    resp = client.post(
        f"/api/apply/{SHORT_PAYLOAD['case_id']}/supplement",
        json={"additional_text": "已补交医疗证明", "attachment_url": "https://example.com/new.pdf"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_review"

    pending = client.get("/api/review/pending", headers=AUTH_HEADER).json()
    assert SHORT_PAYLOAD["case_id"] in {item["case_id"] for item in pending}


def test_supplement_on_non_pending_docs_returns_400(client):
    client.post("/api/apply", json=LONG_PAYLOAD)
    resp = client.post(
        f"/api/apply/{LONG_PAYLOAD['case_id']}/supplement",
        json={"additional_text": "补件"},
    )
    assert resp.status_code == 400


def test_supplement_unknown_case_returns_404(client):
    resp = client.post(
        "/api/apply/does-not-exist/supplement",
        json={"additional_text": "补件"},
    )
    assert resp.status_code == 404
