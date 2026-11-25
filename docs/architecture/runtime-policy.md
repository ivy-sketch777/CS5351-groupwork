# Runtime Policy

> D2 (Architecture) deliverable — Owner: Member 2 (Rule Engine).
> This document specifies the runtime decision policy of the MedLeaveAssist
> rule engine in `src/policy/`.

## 1. Scope

The rule engine is the sole deterministic decision maker for leave
applications. AI is used only for text extraction elsewhere and NEVER decides
outcomes (project red line). The engine is configuration-driven,
deterministic, and fail-closed.

Public contract (backward compatible with the original mock):

```python
from src.policy import evaluate_policy
decision = evaluate_policy(payload, overlap_flag=False, *, today=None)
# -> PolicyDecision (src/schemas.py)
```

## 2. Decision Outcomes

The engine returns a `PolicyDecision` with:

| Field | Meaning |
|-------|---------|
| `result` | `PolicyResult` in {`PASS`, `FAIL_CLOSED`, `ROUTE_TO_REVIEW`} |
| `rule_ids_fired` | IDs of all matched rules (for audit & explanation) |
| `missing_items` | Materials the applicant must supply |
| `is_overlapping` | Whether an approved leave overlaps |
| `reason` | The decisive rule's human-readable explanation |

## 3. Rule Configuration (No Hardcoding)

All rules live in `src/policy/config/policy_v1.0.yaml`. Each rule carries:
`id, priority, description, condition (Python-syntax boolean expression),
action (PolicyResult value), reason`, and optional `add_missing[]` /
`set_overlap`.

Current rule set — **larger priority number is evaluated first**:

| ID | Priority | Condition | Action |
|----|----------|-----------|--------|
| `RULE-INV-003-OVERLAP` | 1000 | `is_overlapping == True` | fail-closed |
| `RULE-FR-007-LONG-LEAVE` | 900 | `duration_days > 3` | route-to-review |
| `RULE-INV-001-INVALID-DATE` | 850 | `is_date_invalid == True` | fail-closed |
| `RULE-FR-003-EVIDENCE-REQUIRED` | 800 | `duration_days > 7 and has_evidence == False` | fail-closed |
| `RULE-FR-003-SHORT-LEAVE` | 100 | `duration_days < 2` | pass |

## 4. Evaluation Semantics

1. Rules are sorted by `priority` descending.
2. The first `fail-closed` hit short-circuits immediately (highest severity).
3. Otherwise all hits are aggregated: `route-to-review` wins over `pass`.
4. If no rule matches, the result defaults to `FAIL_CLOSED`
   (default-deny; never a fake success).

## 5. Condition Evaluation Safety (REQ-SEC-001)

Conditions are parsed with `ast.parse(mode="eval")` and evaluated through a
strict **AST whitelist walker**. No `eval` / `exec` / `compile` is used.

- Allowed nodes: `BoolOp`, `UnaryOp(Not)`, `Compare`, `Name` (resolved from
  the fixed context only), `Constant` (bool / int / None).
- Forbidden: `Call`, `Attribute`, `Subscript`, `BinOp` (incl. `**`), `Lambda`,
  comprehensions, and any statement node.
- Limits: expression length <= 500 chars, <= 200 AST nodes (DoS guard).
- Any violation, unknown variable, name escape, or incompatible-type
  comparison raises `PolicyConfigError`.

## 6. Context Derivation

The engine builds a fixed context dict from the `ApplicationPayload`:

| Key | Type | Derivation |
|-----|------|-----------|
| `duration_days` | int | Number of **teaching days** (Mon–Fri) in the range, inclusive; weekends excluded; public holidays NOT considered. 0 if date invalid. |
| `is_date_invalid` | bool | `start_date > end_date` |
| `has_evidence` | bool | `bool(attachment_url)` |
| `is_overlapping` | bool | Supplied by caller as `overlap_flag`; engine does NOT query the DB. |
| `today` | date | Optional, injected; engine never calls `datetime.now()`. |

> Note (REQ-FR-007): using teaching days means Fri→Mon counts as 2, not 4.

## 7. Fail-Closed Safety Net

Any error — YAML load failure, field validation error, condition evaluation
error, or an unexpected exception — is caught and converted to a
`FAIL_CLOSED` decision with a clear `reason`. `evaluate_policy` never raises
and never returns `PASS` as a fallback.

## 8. Determinism & Performance

- No `datetime.now()`, no randomness. Same input → same outcome (REQ-INV-005),
  verified over 100 repeated runs.
- Rule set is cached per resolved absolute path (`rule_loader`).
  Measured ~0.04 ms per call, far below p95 < 500 ms (REQ-PER-001).

## 9. Module Boundaries & Dependencies on Other Modules

The engine deliberately does NOT reach into other members' modules:

- **Overlap detection (REQ-INV-003)** — needs a DB query of approved leaves by
  the same student; the boolean is passed in as `overlap_flag`. Owner to wire:
  Member 1 (API) + Member 4 (Security/DB).
- **Explanation must include rule IDs (REQ-QUAL-001)** — the API response should
  embed `decision.rule_ids_fired`. Owner: Member 1.
- **Dependency** — `rule_loader` imports `pyyaml`; it must be declared in
  `requirements.txt` (currently missing).

See `docs/` handover note for API integration details.
