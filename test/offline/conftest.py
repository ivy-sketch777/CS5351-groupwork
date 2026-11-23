"""Shared fixtures for the offline governance gate (REQ-GOV-006)."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Repository root; tests must treat it as read-only."""
    return REPO_ROOT
