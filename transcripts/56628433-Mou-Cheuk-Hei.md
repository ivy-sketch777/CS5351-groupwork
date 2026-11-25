# Member 4 Agent Session Transcripts: Security & Governance

Student: Mou Cheuk Hei 56628433 (Member 4)  
Role: Security & Governance Owner  
Agent Tool: Cursor
Module scope: `src/security/`, `src/governance/`, `test/offline/security/`, `test/offline/governance/`  
Hard rules used: `AGENTS.md` (no schema edits, no cross-module writes, plan-then-approve)

---

## Session 1: Security package skeleton & sanitize contract (REQ-SEC-001)

**Goal:** Create `src/security/` helpers that neutralize prompt-injection / policy-override phrases before any model or policy consumption; add offline adversarial tests.

**Plan (agent proposed, human approved before code):**
1. `sanitize_text` + `sanitize_application` only (do not invent new schema types).
2. EN + ZH injection denylist → replace with `[FILTERED]`.
3. Tests under `test/offline/security/test_sanitize.py` first.

**Human Intervention (Red-Line — schemas):**  
Agent suggested adding an `InjectionReport` field to `ApplicationPayload` / `schemas.py`.  
**I rejected** and cited `AGENTS.md`: schemas are frozen; return a cleaned `ApplicationPayload` copy via `deepcopy` instead.

**Human Intervention (Scope):**  
Agent offered to patch `src/core/api.py` to call sanitize immediately.  
**I redirected:** Core wiring is Member 1; deliver stable exports from `src.security` only.

**Outcome:** `sanitize.py` + adversarial tests (ignore-previous-instructions, 强制批准 / 忽略政策). Benign fever text unchanged.

---

## Session 2: PII redaction before LLM (REQ-SEC-002)

**Goal:** Mask student IDs and addresses in LLM-facing text while preserving medical wording.

**Plan approved:**
1. `redact_pii` for free text; `redact_for_llm(payload, extracted_text)` builds the model string.
2. Never include `payload.student_id` in the LLM body; belt-and-suspenders replace if it appears in reason text.
3. Address patterns must stop before `诊断` / `diagnosis` labels so medical content survives.

**Human Intervention (Regex overreach):**  
First agent draft used a greedy `地址:.*` that also swallowed the diagnosis clause.  
**I interrupted**, showed a failing intended case (`住址: … 诊断: 上呼吸道感染`), and required a non-greedy pattern with a diagnosis lookahead. Re-ran `test_redact.py` until diagnosis remained visible and the address became `[REDACTED]`.

**Outcome:** `redact.py` + tests for digit IDs, Chinese 住址, English street addresses, and `redact_for_llm` ID omission.

---

## Session 3: Access control, retention, access log (REQ-SEC-003 / 004)

**Goal:** Least-privilege raw-medical access; 30-day purge helper; log who opened sensitive content.

**Plan approved:**
1. `Role` + `can_view_raw_medical` / `AccessDenied` in `src/security/access.py`.
2. `should_purge(closed_at, now, retention_days=30)` in `retention.py`.
3. `log_sensitive_access` in `src/governance/access_log.py` (in-memory for offline phase).

**Human Intervention (Authority boundary):**  
Agent proposed auto-deleting SQLite rows from `security.retention`.  
**I rejected:** SecGov only decides *whether* to purge; Core/ops owns destructive DB jobs. Keep `should_purge` as a pure function.

**Outcome:** Access allow/deny tests, retention day-29 keep / day-30 purge, access-log actor+timestamp test.

---

## Session 4: Audit + review router + review packet (REQ-GOV-001…004)

**Goal:** Build audit metadata, route low-confidence / missing-doc / conflict cases to humans, and package evidence so advisors cannot rubber-stamp.

**Plan approved:**
1. `build_audit` / `build_system_response` using existing `AuditInfo` / `SystemResponse`.
2. `route_decision` may recommend `in_review` only — **never** `approved`.
3. `build_review_packet` returns a `dict` with derived fields + challenge/escalate/explicit-ack flags.

**Human Intervention (False success):**  
Agent draft set `recommended_status=APPROVED` when confidence ≥ 0.95 and policy PASS.  
**I rejected** as a REQ-INV-001 / project red-line violation. Required a regression test `test_router_never_recommends_approved`.

**Agent self-check (kept):**  
When asked to “just extend schemas with ReviewPacket”, agent refused; human confirmed option: plain `dict` packet, no schema change (same pattern as Member 1’s contract discipline).

**Outcome:** Governance package + router/packet/audit tests green. Documented later as ADR-002.

---

## Session 5: Architecture docs for Member 4 (D2)

**Goal:** Produce `permission-model.md` and ADRs without editing other members’ owned architecture files.

**Human Intervention (Doc scope):**  
Agent started rewriting `invariants.md` / `trace-matrix.md` (Member 1).  
**I stopped** and limited writes to:
- `docs/architecture/permission-model.md`
- `docs/architecture/adr/001-sanitize-redact-before-llm.md`
- `docs/architecture/adr/002-governance-never-auto-approve.md`

**Outcome:** D2 permission model + two ADRs landed; Core integration checklist left open for Member 1.

---

## Cross-session evidence (map to code)

| Theme graders look for | Where it shows up |
|------------------------|-------------------|
| Anti-injection testing | `test/offline/security/test_sanitize.py` |
| Desensitization regex | `src/security/redact.py` + `test_redact.py` |
| Plan approval before code | Sessions 1–4 plan blocks |
| Reject schema / Core drive-by edits | Sessions 1, 4, 5 |
| Never auto-approve from governance | Session 4 + ADR-002 |

**Offline test status (Member 4 suites):** 27 passed (`test/offline/security` + `test/offline/governance`).

---

## Open handoff (not Member 4 code)

- Member 1: call `sanitize` → `redact` → AI → `route_decision` → `build_audit` inside `src/core/api.py`.  
- Member 5: CI gates on safety paths + schema/AI-use-log gates.  
- Member 4 remaining narrative work: D6 chapter「安全边界与数据合规」+ 300–500 word reflection (for `Report.md`).
