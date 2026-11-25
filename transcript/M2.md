# M2 Transcript (Member 2 - Rule Engine Owner)

Theme focus: rule configuration, preventing hardcoded rules.

Full session evidence: `session-ses_e004.md` (repository root).

---

## Event 1 — Contract discovery (read-only)

Reviewed `src/core/mock_policy.py`, `src/core/api.py`, `pytest.ini`, and
`src/schemas.py` in read-only mode to confirm the rule engine contract that
Member 1 expects: `evaluate_policy(payload) -> PolicyDecision`.

Agent clarified the exact enum/field names before any coding:
`PolicyResult` values are `pass` / `fail-closed` / `route-to-review`, and
`PolicyDecision` fields are `rule_ids_fired / missing_items / is_overlapping /
reason`. This prevented contract drift.

## Event 2 — Models (plan approved before coding)

Agent proposed the `Rule` / `RuleSet` dataclasses first; human approved with
two corrections: add a required `description` field (before `condition`) and
rename `is_overlap` to `set_overlap` to match the original requirement
terminology. Priority convention fixed as "smaller number = higher priority"
for the dataclass layer.

## Event 3 — YAML rule config

Agent designed `policy_v1.0.yaml` with 5 rules. Agent caught a semantic flaw:
the assigned priorities (1000 for overlap) contradicted "smaller = higher";
human approved "larger number evaluated first" and the values were kept as-is.
All rules (overlap block, >3-day review, invalid date, >7-day evidence,
<2-day pass) are expressed in YAML — zero hardcoded thresholds in Python.

## Event 4 — Safe condition evaluator

Agent designed an AST-whitelist evaluator (no eval/exec/compile) with limits
for length/node count to prevent DoS and name-escape attacks. Human approved
no BinOp, strict fail-closed on unknown variables.

## Event 5 — Self-audit (Agent-initiated)

Agent performed an independent self-audit and found a real bug: comparing
`None < int` leaked a raw `TypeError`, bypassing fail-closed. Fixed by
wrapping comparisons to raise `PolicyConfigError`, and removed dead constants.
Added two regression tests.

## Event 6 — Rule loader

Agent designed a strict loader with module-level cache keyed by resolved
absolute path, strict unknown-field rejection, bool-is-subclass-of-int guard,
and fail-closed validation. Human approved strict field rejection and exposed
`clear_cache()`.

## Event 7 — Engine + fail-closed safety net

Agent implemented `evaluate_policy` with priority-ordered evaluation,
fail-closed short-circuit, route-over-pass aggregation, and a catch-all
conversion to `FAIL_CLOSED`. Overlap is an explicit `overlap_flag` parameter;
`today` is injectable (no `datetime.now()`).

## Event 8 — Requirements audit correction (REQ-FR-007)

Agent audited the engine against requirement IDs and found `duration_days`
counted calendar days, violating the "consecutive teaching days" requirement.
Fixed to count Mon–Fri only (weekends excluded; no public holidays) and
realigned all tests, adding a Fri→Mon = 2 teaching-day test.

## Outcome

- Outputs confined to `src/policy/` and `test/offline/policy/`.
- `schemas.py` and other members' modules untouched.
- `pytest test/offline/policy -q` → 63 passed.
- No `eval/exec/compile`, no `datetime.now()`, no cross-module imports
  (verified via AST scan).
