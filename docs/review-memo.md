# Review Memo: QA and CI Governance Baseline

- **Status:** Submitted for M1 consolidation
- **Date:** 2026-11-25
- **From:** Member 5 (QA, CI & PM), Tang Man Kit (55641875)
- **To:** Member 1 (integration owner), Members 2-4, Course marker
- **Scope:** CI blocking gate, offline verification suite, traceability, and final-delivery documentation
- **Related records:** `docs/code-governance/verification-constraints.md`, `docs/ci-gate.md`, `docs/trace-matrix.md`, ADR-001 (Member 4)

---

## 1. Purpose

This memo records the review outcome of the QA and governance baseline built by Member 5, the findings that shaped it, and the actions that must be completed by other owners before final delivery. It is written so Member 1 can consolidate the project without re-deriving decisions from chat history.

---

## 2. Review scope

Reviewed artifacts:

- `.github/workflows/ci.yml` (original single-step workflow and its replacement)
- `test/offline/` root-level gate tests and helper modules
- `src/schemas.py` as a frozen contract (read-only)
- `prompts/prompt_v1.0.yaml`, `docs/trace-matrix.md`, root `trace-matrix.md`
- `AGENTS.md` requirement dictionary and workflow rules
- Member 4's ADR-001 (`Sanitize and redact before any LLM call`)
- Member 2's policy-engine handover notes (as quoted in the team PR description)

Out of scope: member-owned source modules under `src/policy/`, `src/ai/`, `src/security/`, `src/governance/`, and member drafts under `docs/drafts/`.

---

## 3. Findings

| # | Finding | Evidence | Consequence |
| --- | --- | --- | --- |
| F1 | The original CI job only ran `pytest test/offline/ -v`; there was no stable required check name and no governance static check | Original `ci.yml` | A broken contract or raw SQL could pass review unnoticed |
| F2 | Governance artifacts were absent: no prompt version file, no trace matrix, no CI self-check | Initial red run: `6 failed, 61 passed` | REQ-GOV-005/006/007 were not satisfiable |
| F3 | The data contract had no structural guard | New `test_schema_contract.py` | A field rename in `schemas.py` would silently break all members |
| F4 | A fabricated leave JSON could be represented as an untyped dict | Negative-control drill: `1 failed, 67 passed`, exit code 1 | Without Pydantic validation, a fake success was representable |
| F5 | The trace matrix parser initially found zero rows | Test bug: regex expected a leading `|` after cell splitting | Gate C would have been vacuously green |
| F6 | The AGENTS priority check produced a false positive | Test bug: the word "cost" appeared earlier in a section heading | A correct document was reported as wrong |
| F7 | Root `trace-matrix.md` was accidentally deleted by a team member | 2026-11-25 user report | Gate C would fail until restored; pointer was regenerated and re-verified |
| F8 | `git status` reports line-ending-only `M` noise on untouched files | `core.autocrlf=true`, LF working tree; `git diff --numstat` shows only real edits in `ci.yml` and `AGENTS.md` | Reviewers must use content diffs, not status flags alone |
| F9 | ADR-001 identifies sanitize -> redact -> AI as the required pre-model order | Member 4 ADR-001 | The order is not yet wired in `src/core/api.py`; tracked as debt |

---

## 4. Decisions locked

1. One blocking job named `blocking-gate` is the only required status check for `main`.
2. Gates A (static governance), B (full offline suite), and C (trace matrix coverage) are mandatory; any failure blocks merge.
3. No `continue-on-error`, no `|| true`, and no conditional skip on pytest steps; this is enforced by a test that parses the YAML.
4. `src/schemas.py` is frozen; contract tests assert exact field sets and closed enums.
5. Static AST checks forbid raw SQL and enforce ORM, module boundaries, and AI non-authority.
6. `docs/trace-matrix.md` is the only traceability source; the root file is a pointer.
7. From 2026-11-25, `ci.yml` and `docs/trace-matrix.md` are M1-owned. M5 will not edit them.
8. Conflict priority is reliability -> input-boundary safety -> accountability -> cost (REQ-QUAL-002).

---

## 5. Action items

| Owner | Item | Why | Exit criteria |
| --- | --- | --- | --- |
| M1 + repository admin | Enable branch protection: require `blocking-gate` on `main`, strict, no bypass | The YAML cannot enable this itself | A red PR cannot be merged; settings screenshot or `gh api` output attached |
| M1 | Take ownership of `.github/workflows/ci.yml`, `docs/trace-matrix.md`, root `trace-matrix.md`, `Report.md` | New fixed-path rule | No M5 edits to these paths after 2026-11-25 |
| M1 | Replace `src/core/mock_policy.py` import with `src.policy.evaluate_policy` | M2 delivered a backward-compatible real engine | Full suite green with real rules; rule IDs visible in student messages |
| M1 + M4 | Query DB for overlapping approved leave and pass `overlap_flag=True` | M2 engine does not read historical state | REQ-INV-003 fail-closed test with a real overlap |
| M1 | Wire sanitize -> redact -> AI before any model call | ADR-001 and REQ-ARCH-004 | Integration test proves no model call when validation or auth fails |
| M3 | Replace `model_version: pending-ai-owner` with the real value and append changelog entries | REQ-GOV-005 and REQ-GOV-001 | Prompt metadata test passes with a real version |
| M3 | Implement token metering with hard cap 3000 | REQ-COST-001 | Test shows zero model calls above the cap |
| M2 | Add p95 benchmark for policy check excluding LLM | REQ-PER-001 | Report shows p95 < 500 ms |
| All members | Update trace matrix rows from Pending to Covered when your module lands | REQ-GOV-007 | Gate C passes with all rows Covered |
| M5 | Maintain `docs/code-governance/`, `docs/review-memo.md`, `docs/debt-register.md`, `docs/bug-diary.md`, `.opencode/permissions.jsonc`, `.agent/rules.md`, D5 transcript | Fixed M5 delivery paths | Files present in English; no red-line path edited |

---

## 6. Review checklist

- [x] `pytest test/offline -q` passes locally before PR (67 passed on 2026-11-25)
- [x] No changes to `src/schemas.py`, `src/core/`, `ci.yml`, or `docs/trace-matrix.md` in this M5 deliverable
- [x] All four governance documents plus permissions, agent rules, and transcript are English
- [x] Negative-control drill performed and temporary file removed
- [x] Previously deleted root trace-matrix pointer restored and re-verified
- [ ] Branch protection configured by administrator
- [ ] Member 1 has completed cross-module consolidation

---

## 7. Sign-off

Code and tests: **green**. Documentation: **complete for M5 scope**. Merge readiness: **conditional** on the two unchecked items above. This memo is submitted to M1 for consolidation; M5 does not merge its own gate changes into M1-owned paths.
