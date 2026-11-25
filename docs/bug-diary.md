# Bug Diary

- **Status:** Living log, reviewed 2026-11-25
- **Owner:** Member 5 (QA, CI & PM), Tang Man Kit (55641875)
- **Scope:** Defects, gate failures, and preventive findings observed during QA and CI work
- **Related:** `docs/code-governance/verification-constraints.md`, `docs/debt-register.md`, ADR-001

Entries are chronological. A "Preventive finding" is recorded when a risk was identified before it could become a production bug.

| Date | ID | Type | Symptom | Root cause | Fix | Verification | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-23 | QA-BUG-001 | Defect | CI ran only `pytest test/offline/ -v`; no governance checks and no stable required check name | Baseline workflow was minimal | Rewrote `ci.yml` as one `blocking-gate` job with Gates A/B/C and a YAML self-check | `test_ci_workflow_is_a_hard_gate` passed | M5 (now M1-owned) | Resolved |
| 2026-11-23 | QA-BUG-002 | Defect | Initial gate run showed `6 failed, 61 passed` because prompt metadata, trace matrix, root pointer, and AGENTS section were missing | Governance artifacts had not been created | Created `prompts/prompt_v1.0.yaml`, `docs/trace-matrix.md`, root pointer, and AGENTS section 6 | Full suite became `67 passed` | M5 | Resolved |
| 2026-11-23 | QA-BUG-003 | Test bug | Trace matrix test parsed zero rows and failed with "contains no requirement rows" | Regex expected a leading `|` after cells had already been stripped | Changed regex to `^(REQ-[A-Z]+-\\d{3})$` | Gate C: `4 passed` | M5 | Resolved |
| 2026-11-23 | QA-BUG-004 | Test bug | AGENTS priority check reported a false failure because the word "cost" appeared earlier in a section heading | Whole-file `find()` instead of scoped search | Scoped search to the line containing the conflict-priority label | `test_agents_documents_conflict_priority` passed | M5 | Resolved |
| 2026-11-23 | QA-BUG-005 | Defect | Fabricated sick-leave JSON could be represented as an untyped dict with an extra `approved` flag | No contract-level rejection test | Added `test_fabricated_sick_leave_json_is_rejected_by_contract` using Pydantic models | Negative drill returned exit code `1` with `1 failed, 67 passed`; temp file removed | M5 | Resolved |
| 2026-11-24 | QA-BUG-006 | Preventive finding | Prompt injection and PII leakage could reach the model before extraction | Uncleaned free text and student identifiers in LLM payload | Member 4 introduced sanitize -> redact helpers and ADR-001 | Security tests pass; API call-order integration still tracked as QA-DEBT-006 | M4 + M1 | Open (integration) |
| 2026-11-25 | QA-BUG-007 | Defect | Root `trace-matrix.md` was accidentally deleted by a team member | Manual file operation outside the gate | Regenerated pointer to `docs/trace-matrix.md`; did not touch the canonical file | `test_root_trace_matrix_pointer` passed (`4 passed`) | M5 (pointer now M1-owned) | Resolved |
| 2026-11-25 | QA-BUG-008 | Environment noise | `git status` listed many untouched files as modified | `core.autocrlf=true` with LF working tree and stale stat cache | No content rewrite performed; used `git diff --numstat` for real changes | Only `ci.yml` and `AGENTS.md` showed real content diffs | M1 (repo hygiene) | Documented |
| 2026-11-25 | QA-BUG-009 | Process risk | M5 could no longer edit `ci.yml` or `docs/trace-matrix.md` after ownership transfer | New fixed-path rule | Recorded in `.opencode/permissions.jsonc` and `.agent/rules.md`; routed gate changes through M1 | No M5 edit to red-line paths in this delivery | M1 + M5 | Mitigated |

---

## Notes on negative-control drill

The deliberate break used a temporary test file containing a fabricated payload:

- `date_range.start_date = "not-a-date"`
- missing `reason_text`
- extra `approved: true` field

Observed result: `1 failed, 67 passed`, process exit code `1`. The file was removed immediately and the suite re-verified at `67 passed`. This is the evidence for REQ-GOV-006's fit criterion that a deliberate break blocks the PR.
