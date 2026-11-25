# Agent Rules - Member 5 (QA, CI & PM)

- **Status:** Active
- **Date:** 2026-11-25
- **Owner:** Member 5, Tang Man Kit (55641875)
- **Scope:** Supplemental operating rules for AI agents working on Member 5 paths
- **Relationship:** This file complements, and does not replace, `.opencode/rules.md`

---

## 1. Absolute red lines

An agent must never edit:

- `src/schemas.py` (the frozen Pydantic contract)
- `src/core/**` (Member 1)
- `.github/workflows/ci.yml` (Member 1 from 2026-11-25)
- `docs/trace-matrix.md` and the root `trace-matrix.md` (Member 1 from 2026-11-25)
- `Report.md` (Member 1 consolidates all drafts)

Cross-module integration, traceability backfill, and conflict resolution are Member 1's job. Member 5 only references these paths in its own records.

## 2. Own paths

An agent may write only to:

- `test/offline/*.py`, `test/offline/conftest.py`, `test/offline/gov_helpers.py`
- `docs/code-governance/**`
- `docs/ci-gate.md`, `docs/review-memo.md`, `docs/debt-register.md`, `docs/bug-diary.md`
- `.opencode/permissions.jsonc`, `.agent/rules.md`
- `transcripts/55641875-Tang Man Kit.md`

All deliverables are written in English.

## 3. Workflow rules

1. **Plan before code.** Output an execution plan and wait for the human approval token ("approved") before creating or editing files.
2. **Tests first.** A new function needs an offline test before any configuration or integration change.
3. **Mock first.** Cross-module dependencies use mocks (for example `src/core/mock_policy.py`) instead of edits to another member's module.
4. **No raw SQL.** Database access must use SQLAlchemy ORM; AST checks enforce this in Gate A.
5. **No fake success.** A failed test must never be hidden with `continue-on-error`, `|| true`, `skip`, or `xfail`.
6. **AI is advisory only.** AI extracts text; it never decides eligibility and never writes the `approved` state.
7. **Verify locally.** Run `pytest test/offline -q` before opening any PR.

## 4. Gate contract

The CI workflow exposes one required status check named `blocking-gate`:

- Gate A: `pytest test/offline/test_ci_governance.py -v --strict-markers`
- Gate B: `pytest test/offline -q --strict-markers --junitxml=artifacts/junit.xml`
- Gate C: `pytest test/offline/test_trace_matrix.py -v --strict-markers`

An agent must not rename the job, add a bypass flag, or move a pytest step behind `if: always()`. The workflow self-check test enforces all of these.

## 5. Evidence and audit

- Record decisions in ADR style: Status, Date, Owner, Related reqs, Context, Decision, Alternatives, Consequences, Reopen conditions, Verification checklist.
- Keep `docs/debt-register.md` current when a fix is explicitly deferred.
- Keep `docs/bug-diary.md` chronological; never delete an entry after it is resolved.
- Any negative-control drill must use a temporary file, record the exit code, remove the file, and re-run the full suite.
- Conflict priority (REQ-QUAL-002): reliability -> input-boundary safety -> accountability -> cost.

## 6. Pre-AI boundary (ADR-001)

Before any model call, the text path must be sanitize -> redact -> AI. Gate A verifies the helper modules and metadata; the actual API call order is Member 1's integration task and remains tracked as QA-DEBT-006.

## 7. Escape hatch

An exception to these rules requires both:

1. explicit human approval in the session, and
2. confirmation from Member 1 when the exception touches a consolidated path.

Without both, the agent refuses the change and reports the conflict instead of editing.
