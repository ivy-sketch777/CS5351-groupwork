"""REQ-GOV-007: the trace matrix must cover every FR and INV requirement."""

import re
from pathlib import Path

EXPECTED_IDS = {
    # Functional requirements
    "REQ-FR-001", "REQ-FR-002", "REQ-FR-003", "REQ-FR-004",
    "REQ-FR-005", "REQ-FR-006", "REQ-FR-007", "REQ-FR-008",
    # Invariants
    "REQ-INV-001", "REQ-INV-002", "REQ-INV-003", "REQ-INV-004", "REQ-INV-005",
    # Architecture
    "REQ-ARCH-001", "REQ-ARCH-002", "REQ-ARCH-003", "REQ-ARCH-004",
    # Security
    "REQ-SEC-001", "REQ-SEC-002", "REQ-SEC-003", "REQ-SEC-004",
    # Cost / performance / quality
    "REQ-COST-001", "REQ-PER-001", "REQ-QUAL-001", "REQ-QUAL-002",
    # Governance
    "REQ-GOV-001", "REQ-GOV-002", "REQ-GOV-003",
    "REQ-GOV-004", "REQ-GOV-005", "REQ-GOV-006", "REQ-GOV-007",
}

ROW_RE = re.compile(r"^(REQ-[A-Z]+-\d{3})$")
TEST_FILE_RE = re.compile(r"test/offline/[A-Za-z0-9_./\\-]+\.py")


def _matrix_rows(repo_root: Path) -> list[tuple[str, list[str]]]:
    text = (repo_root / "docs" / "trace-matrix.md").read_text(encoding="utf-8")
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and ROW_RE.fullmatch(cells[0]):
            rows.append((cells[0], cells))
    return rows


def test_trace_matrix_covers_all_requirements(repo_root: Path) -> None:
    rows = _matrix_rows(repo_root)
    ids = [requirement_id for requirement_id, _ in rows]

    assert ids, "Trace matrix contains no requirement rows"
    assert len(ids) == len(set(ids)), f"Duplicate requirement IDs: {ids}"
    assert set(ids) == EXPECTED_IDS, (
        f"Missing: {sorted(EXPECTED_IDS - set(ids))}; "
        f"Unexpected: {sorted(set(ids) - EXPECTED_IDS)}"
    )

    for requirement_id, cells in rows:
        assert len(cells) >= 5, f"{requirement_id}: row must have 5 columns"
        assert cells[2], f"{requirement_id}: code reference is empty"
        assert cells[3], f"{requirement_id}: test reference is empty"


def test_trace_matrix_test_references_exist(repo_root: Path) -> None:
    for requirement_id, cells in _matrix_rows(repo_root):
        references = TEST_FILE_RE.findall(cells[3])
        assert references, f"{requirement_id}: no test/offline/ file referenced"
        for reference in references:
            path = repo_root / reference.replace("\\", "/")
            assert path.is_file(), f"{requirement_id}: missing test file {reference}"


def test_root_trace_matrix_pointer(repo_root: Path) -> None:
    pointer = repo_root / "trace-matrix.md"
    assert pointer.is_file(), "Root trace-matrix.md pointer is missing"
    assert "docs/trace-matrix.md" in pointer.read_text(encoding="utf-8")


def test_agents_documents_conflict_priority(repo_root: Path) -> None:
    """REQ-QUAL-002: conflict priority order must be recorded in AGENTS.md."""
    text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    priority_lines = [
        line for line in text.splitlines() if "冲突解决优先级" in line
    ]
    assert priority_lines, "AGENTS.md must record the conflict priority"

    order = ["可靠性", "输入边界安全", "可问责性", "成本"]
    positions = [priority_lines[0].find(term) for term in order]
    assert all(position >= 0 for position in positions), (
        f"Conflict priority line must contain all terms: {order}"
    )
    assert positions == sorted(positions), (
        "Conflict priority order must be reliability → boundary safety → accountability → cost"
    )
