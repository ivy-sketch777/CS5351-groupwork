"""Audit who opened sensitive case content and when (REQ-SEC-003)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AccessLogEntry:
    case_id: str
    actor_id: str
    role: str
    action: str
    timestamp: str  # ISO-8601 UTC

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# In-memory store for offline tests / early integration. Core may replace later.
_ACCESS_LOG: list[AccessLogEntry] = []


def clear_access_log() -> None:
    _ACCESS_LOG.clear()


def get_access_log() -> list[AccessLogEntry]:
    return list(_ACCESS_LOG)


def log_sensitive_access(
    *,
    case_id: str,
    actor_id: str,
    role: str,
    action: str = "view_raw_medical",
    timestamp: datetime | None = None,
) -> AccessLogEntry:
    """Record an authorized sensitive-content open (REQ-SEC-003)."""
    ts = timestamp or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    entry = AccessLogEntry(
        case_id=case_id,
        actor_id=actor_id,
        role=str(role),
        action=action,
        timestamp=ts.isoformat(),
    )
    _ACCESS_LOG.append(entry)
    return entry
