# Personal Transcript - 55641875 Tang Man Kit (Member 5)

## Context

Course: CS5351. Project: MedLeaveAssist (Campus Medical Leave Assistant).
Role: Member 5, QA, CI and PM. Owned requirements: REQ-ARCH-002, REQ-GOV-005, REQ-GOV-006, REQ-GOV-007.
This transcript records the human-AI interaction used to produce the QA and governance deliverables, with explicit human-intervention tags.

---

## Entry 1 - 2026-11-23: Task intake and planning

**Human:** Provided the project background, the Member 5 role, the core contract (`src/schemas.py` must not change), the module boundaries, and the workflow rule "plan first, then code, wait for approval". Attached `requirement(2).docx`.

**AI:** Read the DOCX, extracted all 32 requirement IDs, surveyed the repository, and reported that `ci.yml` only ran a single pytest command and that `prompts/`, `docs/`, and the trace matrix did not exist. Produced an execution plan containing the CI YAML structure, the test matrix, and the blocking-rule design. No files were modified.

**[HUMAN INTERVENTION]:** The human replied with the approval token, translated here as "approved". This was the explicit gate that allowed implementation to start.

**Outcome:** Implementation began only after approval, in test-first order.

---

## Entry 2 - 2026-11-23: Test-first gate implementation

**Human:** Required tests first, mocks for other modules, no raw SQL, and no fake success.

**AI:** Created `test/offline/conftest.py`, `gov_helpers.py`, and four test modules before touching configuration. Ran the suite in the pre-fix state and observed `6 failed, 61 passed`: missing prompt file, missing trace matrix, missing root pointer, weak CI self-check, and missing AGENTS conflict-priority section.

**[HUMAN INTERVENTION]:** No mid-task correction was given; the AI self-corrected two of its own test defects (see Entry 3).

**Outcome:** The red state became the evidence that the gate was real, not decorative.

---

## Entry 3 - 2026-11-23: Two test bugs found and fixed by the agent

**AI finding 1:** `test_trace_matrix_covers_all_requirements` parsed zero rows because the regex expected a leading `|` after cells had already been split. Fixed the regex to `^(REQ-[A-Z]+-\\d{3})$` instead of weakening the assertion.

**AI finding 2:** `test_agents_documents_conflict_priority` searched the whole file, so the word "cost" in a section header matched too early. Scoped the search to the line containing the conflict-priority label instead of relaxing the priority order.

**[HUMAN INTERVENTION]:** None; both fixes were recorded in `docs/bug-diary.md` as QA-BUG-003 and QA-BUG-004.

**Outcome:** Gate C passed `4 passed`; full suite reached `67 passed`.

---

## Entry 4 - 2026-11-23: Configuration and documentation generation

**AI:** After the tests were green-capable, rewrote `.github/workflows/ci.yml` as a single `blocking-gate` job, created `prompts/prompt_v1.0.yaml`, `docs/trace-matrix.md`, the root pointer, `docs/ci-gate.md`, and updated `AGENTS.md` with the full requirement dictionary and section 6.

**[HUMAN INTERVENTION]:** The human approved creating `prompts/prompt_v1.0.yaml` even though it was outside the initial "main paths" list, because REQ-GOV-005 names that exact path.

**Outcome:** Full suite: `67 passed`. Gate A: `5 passed`. Gate C: `4 passed`.

---

## Entry 5 - 2026-11-24: Negative-control drill and PR description

**AI:** Temporarily added a failing test containing a fabricated sick-leave JSON payload (invalid date, missing `reason_text`, extra `approved` flag). The suite returned `1 failed, 67 passed` with exit code `1`. Removed the temporary file and re-verified `67 passed`.

**Human:** Asked for a pull request description modelled on Member 2's PR text.

**AI:** Produced a PR description listing closed requirements, CI/governance changes, test evidence, and handover actions.

**[HUMAN INTERVENTION]:** The human supplied the reference PR description; the AI did not invent a merge decision or claim branch protection was already enabled.

**Outcome:** REQ-GOV-006 fit criterion documented with reproducible negative-control evidence.

---

## Entry 6 - 2026-11-25: Accidental deletion recovery

**Human:** "I accidentally deleted the root trace-matrix.md, please regenerate it."

**AI:** Verified `trace-matrix.md` was absent and `docs/trace-matrix.md` was intact, regenerated only the pointer file, and re-ran `test/offline/test_trace_matrix.py` to confirm `4 passed`.

**[HUMAN INTERVENTION]:** The human reported the deletion; the AI did not modify the canonical matrix.

**Outcome:** Root pointer restored; logged as QA-BUG-007.

---

## Entry 7 - 2026-11-25: Ownership change and final M5 deliverables

**Human:** Announced fixed per-member paths and red lines: M5 owns `docs/code-governance/verification-constraints.md`, `docs/review-memo.md`, `docs/debt-register.md`, `docs/bug-diary.md`, `.opencode/permissions.jsonc`, `.agent/rules.md`, and a D5 transcript named with student ID and name. Forbade edits to `src/schemas.py`, `src/core/`, `.github/workflows/ci.yml`, `docs/trace-matrix.md`, and `Report.md`.

**AI:** Acknowledged that `ci.yml` and `docs/trace-matrix.md` had become M1-owned, presented a plan for the seven files, and waited.

**[HUMAN INTERVENTION]:** The human replied (original reply in Chinese, translated here) "approved, and also add .opencode/permissions.jsonc, .agent/rules.md, and the D5 transcript for 55641875 Tang Man Kit". This supplied both the approval and the identity needed for the transcript filename.

**AI:** Created all seven English documents. No red-line path was edited.

**Outcome:** M5 final documentation set complete; branch protection and cross-module consolidation remain M1 actions recorded in `docs/debt-register.md`.

---

## Reflection on human intervention

The decisive interventions were: the initial approval to start coding, the approval to create the prompt-version file outside the original primary path list, the request to model the PR description on a member-supplied example, the report of the deleted pointer, and the final approval with student identity. In every case the AI stopped before editing and resumed only after a clear human instruction. The project's governance rule was preserved throughout: AI produced text, tests, and records, while humans owned approval, merge decisions, and repository administration.
