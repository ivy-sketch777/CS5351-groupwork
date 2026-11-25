# Verification Constraints: CI Blocking Gate and Traceability

- **Status:** Accepted
- **Date:** 2026-11-25
- **Owner:** Member 5 (QA, CI & PM), Tang Man Kit (55641875)
- **Deciders:** Member 5 (proposal), Member 1 (integration owner), Repository administrator (branch protection)
- **Related reqs:** REQ-ARCH-002, REQ-GOV-005, REQ-GOV-006, REQ-GOV-007, REQ-QUAL-002, REQ-FR-004, REQ-INV-001, REQ-INV-002
- **Enforcing code:** `.github/workflows/ci.yml` (M1-owned from 2026-11-25), `test/offline/test_ci_governance.py`, `test/offline/test_schema_contract.py`, `test/offline/test_integration_flow.py`, `test/offline/test_trace_matrix.py`, `test/offline/conftest.py`, `test/offline/gov_helpers.py`
- **Tests:** 67 offline tests total (5 governance static, 9 schema contract, 5 integration, 4 trace matrix, plus existing member tests)
- **Reference ADR:** [ADR-001: Sanitize and redact before any LLM call](../architecture/adr/001-sanitize-redact-before-llm.md) (Member 4)

---

## Context

MedLeaveAssist is built by five members in parallel. The highest project red line is that AI may only extract text and must never decide a leave outcome; no interface may return a fake success. The original CI workflow ran a single `pytest test/offline/ -v` command with no stable required status check, no governance static checks, and no traceability enforcement. That setup could not satisfy REQ-GOV-005/006/007 and could not prove that a deliberate break (for example, a fabricated sick-leave JSON) would block a merge.

This record locks the verification constraints that Member 5 introduced, in the same ADR style used by Member 4's ADR-001, so that later changes can be reviewed against a fixed baseline. From 2026-11-25 the workflow file and the trace matrix are owned by Member 1; Member 5 only references them here and no longer edits them.

---

## Decision

Adopt a **deterministic, fail-closed verification baseline**:

```
PR / push
   |
   v
blocking-gate  (one job, one required status check)
   |
   +-- Gate A: governance static checks  (test_ci_governance.py)
   +-- Gate B: full offline suite        (test/offline)
   +-- Gate C: trace matrix coverage     (test_trace_matrix.py)
   |
   v
Any failure -> job fails -> GitHub rejects merge
```

Concrete constraints:

1. **Single atomic gate.** The workflow defines exactly one job named `blocking-gate`. That exact string is the required status check for `main`. Gate A, Gate B and Gate C run inside that job; there is no separate optional job whose failure can be ignored.

2. **No bypass tokens.** No `continue-on-error: true`, no `|| true`, and no `if: always()` / `if: cancelled()` on any step that runs `pytest`. The only `if: always()` step is the JUnit evidence upload, which does not affect the verdict. `test_ci_workflow_is_a_hard_gate` parses the YAML and fails if any of these rules is broken.

3. **Static governance checks (AST-based).** All files under `src/` are scanned without importing them:
   - forbidden: `import sqlite3`, raw SQL string literals, `execute()` with a SQL literal, `sqlalchemy.text()`, raw `cursor()`;
   - any module using database calls must import SQLAlchemy ORM;
   - `src/ai/` must not import `src/policy/`, `src/policy/` must not import `src/ai/`, and AI code must not emit `CaseStatus.APPROVED` or an `approved` literal. These checks enforce REQ-ARCH-002 and REQ-ARCH-001.

4. **Prompt version metadata.** `prompts/prompt_v1.0.yaml` must exist, parse as YAML, and contain non-empty `prompt_id`, `version`, `model_version`, and `changelog`. The version must match the filename and `authority` must be `extraction_only` (REQ-GOV-005, REQ-INV-002).

5. **Frozen data contract.** `src/schemas.py` is read-only. Tests assert the exact field sets of `ApplicationPayload`, `ExtractionResult`, `ExtractedField`, `PolicyDecision`, `AuditInfo`, `SystemResponse`, and the closed enum values. Fabricated sick-leave JSON (invalid date, missing `reason_text`, extra `approved` flag) must raise `ValidationError`.

6. **Traceability.** `docs/trace-matrix.md` must contain all 32 requirement IDs (8 FR + 5 INV + 4 ARCH + 4 SEC + COST + PERF + 2 QUAL + 7 GOV), no duplicates, with non-empty code and test references, and every referenced `test/offline/` file must exist. The root `trace-matrix.md` is a pointer only.

7. **Test-first and mock-first.** Every new function needs an offline test before integration. Cross-module dependencies use mocks (for example `src/core/mock_policy.py`) rather than edits to another member's module.

8. **Pre-AI order remains a separate integration debt.** ADR-001 fixes the order sanitize -> redact -> AI. Gate A verifies the helper modules exist and are tested, but the actual call order in `src/core/api.py` is Member 1's integration work and is tracked in `docs/debt-register.md` (QA-DEBT-006).

9. **Conflict priority.** All review decisions follow REQ-QUAL-002: reliability -> input-boundary safety -> accountability -> cost. This order is recorded in `AGENTS.md` section 6 and checked by `test_agents_documents_conflict_priority`.

---

## Alternatives considered

| Option | Summary | Why rejected or deferred |
| --- | --- | --- |
| A. Human PR review only | Reviewers inspect code manually | Not deterministic, does not scale, cannot machine-check "fake success" |
| B. Let failed tests merge and fix later | Mark red jobs as advisory | Directly violates REQ-GOV-006 and the no-fake-success red line |
| C. Runtime-only guards in the API | Validate at request time, skip CI | Too late; a bad merge can reach deployment before runtime detection |
| D. Full security/compliance platform | Enterprise DLP and policy engine | Out of scope and cost for a coursework project |
| **E. Three-gate blocking CI + AST checks + trace matrix (chosen)** | Deterministic, offline, auditable | Satisfies REQ-ARCH-002, REQ-GOV-005/006/007 with zero model calls |

---

## Consequences

### Positive

- A failed test, a raw SQL pattern, a missing prompt version, or a missing requirement ID all produce the same visible red check: `blocking-gate`.
- The negative-control drill (temporary fabricated leave JSON) returned exit code 1 with `1 failed, 67 passed`, proving the gate can block.
- Schema drift is detected structurally, without hashing the file, so harmless formatting changes do not create false alarms.
- Member boundaries are machine-enforced at import level, reducing merge conflict risk during parallel development.

### Negative / tradeoffs

- Branch protection itself is a GitHub repository setting; the workflow only produces the red status. Until an administrator adds `blocking-gate` as a required check on `main`, a red PR cannot be auto-merged by GitHub rules.
- `prompts/prompt_v1.0.yaml` currently carries the placeholder `model_version: pending-ai-owner`; Member 3 must replace it with the real model version.
- Ownership of `ci.yml` and `docs/trace-matrix.md` moved to Member 1 on 2026-11-25. Member 5 can no longer repair those files directly and must route changes through M1.
- The AST denylist is conservative: a legitimate future SQLAlchemy `text()` usage would be blocked and require an explicit review, not a silent exemption.

### Neutral

- ADR-001 covers the pre-LLM input boundary; this record covers the verification boundary. They are complementary, not overlapping.
- Local verification used Python 3.11; the CI workflow pins Python 3.10. Both run the same `test/offline` suite.

---

## Reopen conditions

Revisit this record if any of the following occur:

1. A red `blocking-gate` check is merged or bypassed in a demonstrated PR.
2. The required check name changes from `blocking-gate` to anything else.
3. `src/schemas.py` gains or loses a field through an approved contract change.
4. A member other than M1 modifies `.github/workflows/ci.yml`, `docs/trace-matrix.md`, or the root pointer.
5. Trace matrix coverage drops below 100% of FR and INV.
6. Branch protection is disabled or `Do not allow bypassing` is unchecked.

---

## Verification checklist

| Check | Command | Expected evidence |
| --- | --- | --- |
| Full offline gate | `pytest test/offline -q --strict-markers` | `67 passed` on the current baseline |
| Governance static | `pytest test/offline/test_ci_governance.py -v` | `5 passed` |
| Trace coverage | `pytest test/offline/test_trace_matrix.py -v` | `4 passed` |
| Contract rejection | `pytest test/offline/test_schema_contract.py -q` | fabricated JSON raises `ValidationError` |
| Negative control | temporary failing test with fake leave JSON | exit code `1`; temp file removed afterwards |
| Required check (admin) | GitHub Settings -> Branches -> protection rule | `blocking-gate` is required on `main`, strict, no bypass |

---

## Handoff

Member 1 owns `.github/workflows/ci.yml`, `docs/trace-matrix.md`, `trace-matrix.md`, and the final `Report.md`. Member 5 retains `test/offline/` root-level gate files and the `docs/code-governance/` record set. Any change to the gate must keep this document and `docs/ci-gate.md` in sync.
