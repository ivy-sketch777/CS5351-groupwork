# ADR-002: Governance recommends review, never auto-approve

- **Status:** Accepted  
- **Date:** 2026-11-24  
- **Owner:** Member 4 (Security & Governance)  
- **Deciders:** Member 4 (proposal), Member 1 (state machine / write path), Member 2 (policy signals)  
- **Related reqs:** REQ-GOV-001, REQ-GOV-002, REQ-GOV-003, REQ-GOV-004, REQ-INV-001, INV-001, INV-002, INV-005  
- **Enforcing code:**  
  - `src/governance/review_router.py`  
  - `src/governance/review_packet.py`  
  - `src/governance/audit.py`  
  - `src/governance/access_log.py`  
- **Tests:** `test/offline/governance/test_review_router.py`, `test/offline/governance/test_audit.py`

---

## Context

Leave approval is a consequential campus decision. The system uses AI extraction and a deterministic policy engine, then may place cases in a human queue. Two failure modes are unacceptable:

1. **False success** — returning or recommending `approved` without mandatory rules and (when required) human review.
2. **Rubber-stamping** — advisors see an opaque AI summary and click approve without evidence, derived-field tags, or challenge/escalate options.

Member 4 owns governance helpers that **route and package** review work. Member 1 owns the authoritative state machine and DB writes. Member 2 owns `PolicyDecision` signals such as `route-to-review` and `fail-closed`.

---

## Decision

### 1. Review router never recommends `approved`

`route_decision(...)` may return:

| Situation | `should_review` | `recommended_status` |
|-----------|:---------------:|----------------------|
| No review triggers | `false` | `draft` (status left to Core/policy; not a write) |
| Any trigger (low confidence, missing docs, red flag, policy route/fail-closed/overlap, …) | `true` | **`in_review` only** |

Hard rule: **`recommended_status` must never be `CaseStatus.APPROVED`.**  
Approval remains exclusive to the human review path in Core (after policy constraints).

### 2. Review packet is evidence-first (anti rubber-stamp)

`build_review_packet(...)` always exposes:

- Evidence snippets  
- Derived fields with exact values + `derived` + `confidence` (REQ-GOV-004)  
- Policy summary (`result`, fired rules, missing items, overlap, reason)  
- Actions: `challenge_allowed`, `escalate_allowed`, `approve_requires_explicit_ack` = true (REQ-GOV-003)

Returned as a plain `dict` so we do **not** extend `schemas.py`.

### 3. Audit metadata is mandatory for consequential responses

`build_audit` requires non-empty `actor` and `rule_version`; optional `model_version` / `prompt_version` for AI-touched paths (REQ-GOV-001 / INV-005).  
`build_system_response` embeds that audit into `SystemResponse`.

### 4. Sensitive views are logged

Authorized raw-medical opens go through `log_sensitive_access` (REQ-SEC-003), complementary to ADR-001’s input gates.

---

## Alternatives considered

| Option | Summary | Why rejected |
|--------|---------|--------------|
| A. Auto-approve when policy `PASS` and confidence high | Fast student UX | Violates REQ-INV-001 / INV-001 when docs/human gates still required; high false-success risk |
| B. Let LLM choose `approved` / `rejected` | Single-model decision | Violates project red line and INV-002 |
| C. Governance writes case status directly | SecGov owns DB transitions | Breaks module boundaries; Core must remain sole write authority |
| **D. Advisory router + evidence packet (chosen)** | Recommend `in_review` only; Core/human decide | Preserves invariants and Member boundaries |

---

## Consequences

### Positive

- Clear fail-safe: governance cannot invent approval.
- Advisors get challenge/escalate/ack hooks instead of a single green button narrative.
- Offline tests lock “never recommends approved” and derived-field visibility.
- Fits low-coupling rule: Core consumes public exports only.

### Negative / tradeoffs

- More cases may land in `in_review` (operational load) when confidence thresholds are conservative (default `0.6`).
- Access log is in-memory until Core persists it — acceptable for offline phase, debt for production.
- Router recommends `draft` when idle; Core must not treat that as a persisted state write without its own logic.

### Coordination

- Member 1 must call `route_decision` / `build_review_packet` / `build_audit` at the correct points; SecGov does not patch `src/core/`.
- Member 2’s `PolicyResult.ROUTE_TO_REVIEW` / `FAIL_CLOSED` / `is_overlapping` are first-class router inputs.

---

## Reopen conditions

1. Product policy explicitly allows auto-approve for a narrow, documented class (e.g. ≤1 day, complete docs, policy PASS) **and** a new invariant + ADR amend it.  
2. Trace/monitor evidence shows systematic over-routing that blocks campus operations.  
3. Schema owners add a first-class `ReviewPacket` model (would replace the plain-dict approach).

---

## Verification checklist

- [x] `test_router_never_recommends_approved`
- [x] Low confidence / missing docs / policy route / red flag → `in_review`
- [x] Review packet shows derived exact values + challenge/escalate flags
- [x] `build_audit` rejects empty actor
- [ ] Core persists audit versions on every consequential decision (Member 1 + INV-005)
- [ ] Access log persisted beyond in-memory store (integration)
