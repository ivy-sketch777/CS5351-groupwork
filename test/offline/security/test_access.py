"""Access control and retention tests (REQ-SEC-003, REQ-SEC-004)."""

from datetime import datetime, timedelta, timezone

import pytest

from src.governance.access_log import clear_access_log, get_access_log, log_sensitive_access
from src.security.access import AccessDenied, Role, assert_can_view_raw_medical, can_view_raw_medical
from src.security.retention import should_purge


def test_student_can_view_own_case():
    assert can_view_raw_medical(Role.STUDENT, "87654321", "87654321") is True


def test_student_cannot_view_others_case():
    assert can_view_raw_medical(Role.STUDENT, "87654321", "11111111") is False


def test_advisor_can_view():
    assert can_view_raw_medical(Role.ADVISOR, "87654321", "advisor-1") is True


def test_unknown_role_denied():
    assert can_view_raw_medical("guest", "87654321", "guest-1") is False


def test_assert_raises_on_deny():
    with pytest.raises(AccessDenied):
        assert_can_view_raw_medical(Role.STUDENT, "87654321", "11111111")


def test_authorized_access_is_logged_with_actor_and_time():
    clear_access_log()
    ts = datetime(2026, 11, 14, 10, 0, 0, tzinfo=timezone.utc)
    entry = log_sensitive_access(
        case_id="case-9",
        actor_id="advisor-1",
        role=Role.ADVISOR.value,
        timestamp=ts,
    )
    assert entry.actor_id == "advisor-1"
    assert entry.timestamp == ts.isoformat()
    logs = get_access_log()
    assert len(logs) == 1
    assert logs[0].case_id == "case-9"
    assert logs[0].actor_id == "advisor-1"


def test_retention_before_30_days_keeps():
    closed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = closed + timedelta(days=29)
    assert should_purge(closed, now=now, retention_days=30) is False


def test_retention_on_day_30_purges():
    closed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now = closed + timedelta(days=30)
    assert should_purge(closed, now=now, retention_days=30) is True
