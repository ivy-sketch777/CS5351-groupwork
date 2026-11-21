"""Least-privilege access to raw medical content (REQ-SEC-003)."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    STUDENT = "student"
    ADVISOR = "advisor"
    ADMIN = "admin"


class AccessDenied(PermissionError):
    """Raised when an actor may not view raw medical content."""


def can_view_raw_medical(role: str | Role, case_owner_id: str, actor_id: str) -> bool:
    """Return True if actor may see raw medical content for the case.

    - student: only their own case
    - advisor / admin: allowed
    - anything else: denied
    """
    role_value = role.value if isinstance(role, Role) else str(role).lower().strip()
    if role_value in (Role.ADVISOR.value, Role.ADMIN.value):
        return True
    if role_value == Role.STUDENT.value:
        return bool(actor_id) and actor_id == case_owner_id
    return False


def assert_can_view_raw_medical(role: str | Role, case_owner_id: str, actor_id: str) -> None:
    """Raise AccessDenied if the actor cannot view raw medical content."""
    if not can_view_raw_medical(role, case_owner_id, actor_id):
        raise AccessDenied(
            f"actor={actor_id!r} role={role!r} cannot view raw medical content "
            f"for case owner={case_owner_id!r}"
        )
