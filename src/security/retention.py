"""Sensitive working-copy retention (REQ-SEC-004)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def should_purge(
    closed_at: datetime,
    now: datetime | None = None,
    retention_days: int = 30,
) -> bool:
    """Return True when a closed case's working copy should be purged.

    Purge when ``now >= closed_at + retention_days`` (inclusive of the boundary).
    """
    if retention_days < 0:
        raise ValueError("retention_days must be >= 0")
    if closed_at.tzinfo is None:
        closed_at = closed_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current >= closed_at + timedelta(days=retention_days)
