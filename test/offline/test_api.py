import os
import sys

from fastapi.testclient import TestClient

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from core.api import app  # noqa: E402

client = TestClient(app)

VALID_PAYLOAD = {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "student_id": "2024001",
    "course_id": "COMP999",
    "date_range": {"start_date": "2026-11-01", "end_date": "2026-11-03"},
    "reason_text": "感冒发烧，需要休息",
    "attachment_url": "https://example.com/medical.pdf",
}


def test_apply_returns_draft_successfully():
    resp = client.post("/api/apply", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == VALID_PAYLOAD["case_id"]
    assert body["status"] == "draft"
    assert body["message"] == "申请已受理，正在等待材料提取"
    assert body["audit"]["actor"] == "system"
    assert body["audit"]["rule_version"] == "v1.0"


def test_apply_missing_required_field_returns_422():
    bad = dict(VALID_PAYLOAD)
    del bad["student_id"]
    resp = client.post("/api/apply", json=bad)
    assert resp.status_code == 422


def test_apply_without_attachment_succeeds():
    no_attach = dict(VALID_PAYLOAD)
    no_attach.pop("attachment_url", None)
    resp = client.post("/api/apply", json=no_attach)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"
