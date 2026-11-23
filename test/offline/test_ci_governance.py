"""Static governance gate: REQ-GOV-005, REQ-ARCH-002, REQ-GOV-006 self-check."""

from pathlib import Path

import yaml

from test.offline.gov_helpers import (
    cross_module_imports,
    imported_roots,
    parse_module,
    python_files,
    raw_sql_violations,
    uses_database,
    writes_approved,
)


def test_no_raw_sql_and_orm_required(repo_root: Path) -> None:
    """AGENTS.md rule: database access must use ORM, never raw SQL."""
    files = python_files(repo_root)
    files = [f for f in files if "rule_loader.py" not in str(f)]
    assert files, "No source files found - gate would pass vacuously"

    violations = {
        str(path.relative_to(repo_root)).replace("\\", "/"): raw_sql_violations(path)
        for path in files
    }
    violations = {name: msgs for name, msgs in violations.items() if msgs}
    assert violations == {}, f"Raw SQL detected: {violations}"

    db_files = [path for path in files if uses_database(parse_module(path))]
    assert db_files, "No ORM usage found - gate would pass vacuously"
    non_orm = [
        str(path.relative_to(repo_root)).replace("\\", "/")
        for path in db_files
        if "sqlalchemy" not in imported_roots(parse_module(path))
    ]
    assert non_orm == [], f"Database modules without SQLAlchemy ORM import: {non_orm}"


def test_rules_file_exists_and_nonempty(repo_root: Path) -> None:
    """REQ-GOV-005: .opencode/rules.md must exist and carry actual rules."""
    path = repo_root / ".opencode" / "rules.md"
    assert path.is_file(), "Missing .opencode/rules.md (REQ-GOV-005)"
    assert path.read_text(encoding="utf-8").strip(), ".opencode/rules.md is empty"


def test_prompt_version_file_contains_required_metadata(repo_root: Path) -> None:
    """REQ-GOV-005: prompts/prompt_v1.0.yaml is parseable and versioned."""
    path = repo_root / "prompts" / "prompt_v1.0.yaml"
    assert path.is_file(), "Missing prompts/prompt_v1.0.yaml (REQ-GOV-005)"

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Prompt version file must be a YAML mapping"

    for key in ("prompt_id", "version", "model_version", "changelog"):
        assert key in data, f"Prompt metadata missing key: {key}"
        assert data[key] not in (None, "", [], {}), f"Prompt metadata empty: {key}"

    version = str(data["version"])
    assert version.replace("v", "") in path.stem, "Prompt version must match filename"
    assert data.get("authority") == "extraction_only", (
        "Prompt metadata must state that AI has no decision authority (REQ-INV-002)"
    )


def test_extractor_policy_summarizer_module_boundaries(repo_root: Path) -> None:
    """REQ-ARCH-002: policy changes must not require AI code changes (or vice versa)."""
    ai_dir = repo_root / "src" / "ai"
    policy_dir = repo_root / "src" / "policy"

    if ai_dir.is_dir():
        for path in sorted(ai_dir.rglob("*.py")):
            rel = str(path.relative_to(repo_root)).replace("\\", "/")
            assert not cross_module_imports(path, "policy"), (
                f"{rel} must not import the policy engine (REQ-ARCH-002)"
            )
            assert not writes_approved(path), (
                f"{rel} must never emit the approved state (REQ-ARCH-001)"
            )

    if policy_dir.is_dir():
        for path in sorted(policy_dir.rglob("*.py")):
            rel = str(path.relative_to(repo_root)).replace("\\", "/")
            assert not cross_module_imports(path, "ai"), (
                f"{rel} must not import AI extraction code (REQ-ARCH-002)"
            )

    mock_policy = repo_root / "src" / "core" / "mock_policy.py"
    if mock_policy.is_file():
        assert not cross_module_imports(mock_policy, "ai"), (
            "Deterministic policy mock must not depend on AI modules"
        )


def test_ci_workflow_is_a_hard_gate(repo_root: Path) -> None:
    """REQ-GOV-006: the workflow itself must be strict and non-bypassable."""
    path = repo_root / ".github" / "workflows" / "ci.yml"
    assert path.is_file(), "Missing .github/workflows/ci.yml"

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "ci.yml must be a YAML mapping"

    # PyYAML 1.1 parses the key `on` as boolean True.
    triggers = data.get("on", data.get(True)) or {}
    assert "pull_request" in triggers, "CI must run on pull requests"
    assert "main" in triggers["pull_request"].get("branches", []), (
        "PRs targeting main must be gated"
    )

    assert data.get("permissions", {}).get("contents") == "read", (
        "Gate should use least-privilege permissions"
    )

    jobs = data.get("jobs") or {}
    assert "blocking-gate" in jobs, "Required check job must be named 'blocking-gate'"
    job = jobs["blocking-gate"]
    assert job.get("name") == "blocking-gate", "Job display name must be stable"

    steps = job.get("steps") or []
    runs = [str(step.get("run", "")) for step in steps]
    assert any("pytest test/offline" in run for run in runs), (
        "Full offline suite must run in the blocking gate"
    )
    assert any("test/offline/test_ci_governance.py" in run for run in runs), (
        "Governance static checks must run as a named gate"
    )
    assert any("test/offline/test_trace_matrix.py" in run for run in runs), (
        "Trace matrix coverage must run as a named gate"
    )

    assert not any("continue-on-error" in str(step).lower() for step in steps), (
        "continue-on-error would allow a fake success (REQ-FR-004)"
    )
    assert not any("|| true" in run for run in runs), (
        "Failure swallowing is forbidden in the blocking gate"
    )
    for step in steps:
        if "pytest" in str(step.get("run", "")):
            condition = str(step.get("if", "")).lower()
            assert "always" not in condition and "cancelled" not in condition, (
                "Test steps must fail the job when tests fail"
            )
