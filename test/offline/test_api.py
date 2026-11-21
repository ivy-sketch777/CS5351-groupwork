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

from src.core.api import app  # noqa: E402
from src.core.database import Base, get_db  # noqa: E402

VALID_PAYLOAD = {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "student_id": "2024001",
    "course_id": "COMP999",
    "date_range": {"start_date": "2026-11-01", "end_date": "2026-11-03"},
    "reason_text": "感冒发烧，需要休息",
    "attachment_url": "https://example.com/medical.pdf",
}


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


def test_apply_persists_and_returns_draft(client):
    resp = client.post("/api/apply", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == VALID_PAYLOAD["case_id"]
    assert body["status"] == "draft"
    assert body["message"] == "申请已受理，正在等待材料提取"
    assert body["audit"]["actor"] == "system"
    assert body["audit"]["rule_version"] == "v1.0"


def test_status_returns_persisted_case(client):
    client.post("/api/apply", json=VALID_PAYLOAD)
    resp = client.get(f"/api/status/{VALID_PAYLOAD['case_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == VALID_PAYLOAD["case_id"]
    assert body["status"] == "draft"
    assert body["audit"]["actor"] == "system"


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
    assert resp.json()["status"] == "draft"
