# D6 Contribution — Member 4

**Author:** Mou Cheuk Hei (56628433)  
**Role:** Security & Governance Owner  
**For:** merge into root `Report.md` by Member 5 (PM)  
**Sections below:** (A) 安全边界与数据合规 / Security Boundaries & Data Compliance · (B) Personal reflection (≈400 words)

---

## A. Security Boundaries and Data Compliance  
### （报告章节：安全边界与数据合规）

### A.1 Why this boundary exists

MedLeaveAssist uses an LLM only to **extract** fields from leave reasons and medical text. Eligibility and approval must stay with **deterministic policy code** and **human counselors**. That split creates a hard security/governance boundary: anything that reaches the model, anything that reaches an advisor’s screen, and anything that can change case status must be constrained so the team cannot ship a “fake success” or leak student identity to a model provider.

Member 4 owns two packages that encode this boundary without owning the Core write path:

| Package | Responsibility |
|---------|----------------|
| `src/security/` | Sanitize free text, redact PII, least-privilege access checks, retention decision helper |
| `src/governance/` | Audit metadata, review routing advice, human-review evidence packets, sensitive-access logging |

Architecture decisions are recorded in ADR-001 (sanitize → redact before LLM) and ADR-002 (governance never recommends `approved`). File-level agent rights and runtime roles are in `docs/architecture/permission-model.md`.

### A.2 Pre-AI input gate (REQ-SEC-001 / REQ-SEC-002)

**Threat.** Free-text fields can carry prompt-injection and policy-override language (“ignore previous instructions”, “强制批准”). The same fields may embed student IDs and addresses that must not leave the campus trust boundary.

**Control.**

1. `sanitize_text` / `sanitize_application` replace known EN/ZH injection patterns with `[FILTERED]` before downstream use.  
2. `redact_pii` / `redact_for_llm` mask IDs and address cues, omit `student_id` from the LLM-facing string, and try to preserve medical wording (e.g. stop address redaction before a `诊断` / `diagnosis` label).

**Call order (contract for Core):**

```text
validate payload → sanitize → redact → (only then) AI extract if ai_allowed
```

This matches REQ-ARCH-004 and ADR-001. Member 4 ships the helpers and offline adversarial tests; Member 1 must wire them into `src/core/api.py` so the live path cannot bypass the gate.

**Evidence.** `test/offline/security/test_sanitize.py`, `test/offline/security/test_redact.py` (injection neutralized; IDs/addresses redacted; diagnosis text retained in the designed cases).

### A.3 Least privilege, access logging, retention (REQ-SEC-003 / REQ-SEC-004)

**Runtime roles** (`src/security/access.py`):

- `student` — raw medical content only for own case (`actor_id == case_owner_id`)  
- `advisor` / `admin` — allowed  
- any other role — denied (`AccessDenied`)

**Accountability.** `log_sensitive_access` records `case_id`, `actor_id`, `role`, `action`, and UTC timestamp when sensitive content is opened. The offline store is in-memory; persistence is an integration item for Core.

**Retention.** `should_purge` returns true when `now >= closed_at + 30 days` for closed-case working copies. SecGov decides *whether* purge is due; destructive deletion remains an ops/Core job so a coding agent cannot “helpfully” wipe production rows from the security module.

**Evidence.** `test/offline/security/test_access.py`.

### A.4 Governance: audit, routing, anti rubber-stamp (REQ-GOV-001…004)

**Audit.** `build_audit` requires non-empty `actor` and `rule_version`, and accepts optional `model_version` / `prompt_version`, aligning with INV-005 (consequential decisions must be versioned).

**Routing.** `route_decision` sends low-confidence extraction, missing documents, red flags, and policy `route-to-review` / fail-closed / overlap signals to **`in_review`**. It **never** recommends `CaseStatus.APPROVED` (ADR-002; REQ-INV-001). When there is no trigger, it leaves status to Core/policy rather than inventing an approval.

**Review packet.** `build_review_packet` gives advisors evidence snippets, derived fields with exact values + `derived` + `confidence`, policy summary, and action flags (`challenge_allowed`, `escalate_allowed`, `approve_requires_explicit_ack`). The packet is a plain `dict` so `schemas.py` stays untouched.

**Evidence.** `test/offline/governance/test_review_router.py`, `test_audit.py` — including `test_router_never_recommends_approved`.

### A.5 Authority map (who may decide what)

| Actor / component | May advise | May decide approve/reject | Notes |
|-------------------|:----------:|:-------------------------:|-------|
| LLM extraction | Yes | No | Advisory `ExtractionResult` only |
| Security sanitize/redact | Gate inputs | No | Mandatory before AI |
| Governance router / packet | Yes (`in_review`) | No | Never recommends `approved` |
| Policy engine | Pass / fail-closed / route | Constrains Core | Deterministic rules |
| Human counselor via Core | — | Yes | Sole approval authority after review gates |

### A.6 Residual risk and debt

| Residual risk | Mitigation / debt |
|---------------|-------------------|
| Regex denylist will miss novel injections | Guardrail debt; expand patterns from bug-diary incidents; consider allowlisted structured fields later |
| Helpers not yet called from Core apply path | Integration dependency on Member 1; tracked in ADR-001 checklist |
| In-memory access log | Must move to durable store before production claims |
| Over-routing to humans if confidence threshold is low | Tune threshold with Member 2/1 using review backlog metrics |

### A.7 Summary for the process report

Member 4’s contribution is a **deterministic safety shell** around an advisory AI: clean and redact inputs, restrict who sees raw medical data, force auditable metadata, and route uncertain cases to humans with evidence—not a green “AI said OK” button. Offline suites under `test/offline/security` and `test/offline/governance` currently report **27 passed**. End-to-end compliance still requires Core to invoke these APIs on the authoritative request path.

---

## B. Personal reflection (Member 4)

Working as Security & Governance owner taught me that in an agentic project the hardest part is not writing another helper function—it is **stopping the agent and teammates from optimizing away the safety boundary**. Early plans from the coding agent repeatedly drifted toward editing `schemas.py`, auto-approving high-confidence cases, or deleting database rows from the retention module. Each time, the useful move was the same: point at `AGENTS.md` and the invariants, reject the change, and ask for a narrower plan that stayed inside `src/security` and `src/governance`.

I also learned to treat **tests as the real specification**. Adversarial sanitize cases in English and Chinese, redaction cases that must keep diagnosis text, and `test_router_never_recommends_approved` matter more than a prose claim that we are “secure.” When a greedy address regex swallowed the medical clause, the failing intended example forced a better pattern; that debugging loop felt closer to real security engineering than adding more comments.

Coordination was as important as code. ADR-001 and the permission model make an explicit handoff: I provide gates; Member 1 owns call order; Member 3 consumes only cleaned text; Member 5 must eventually gate safety paths in CI. Until Core wires sanitize and redact, our controls are correct in isolation but not yet enforced on the live apply path—an honest gap that belongs in the report rather than being hidden.

Finally, using Cursor under human approval changed how I supervise AI. I now start every task with “plan only,” refuse schema and foreign-module edits by default, and annotate interventions for the transcript. The agent is fast at scaffolding; the human is responsible for **authority**—what may never be approved, what may never be sent to the model, and what may never be written by the wrong role. That discipline is the main skill I take from CS5351 into later AI-assisted work.

*(Word count ≈ 390; adjust slightly after you personalize one concrete anecdote from your real chat log.)*

---

## C. Merge checklist for Member 5

- [ ] Paste **Section A** into `Report.md` under the security chapter heading  
- [ ] Paste **Section B** into the individual reflections appendix (label: Mou Cheuk Hei / 56628433)  
- [ ] Cross-link ADR-001, ADR-002, `permission-model.md`, and `transcript/M4.md`  
- [ ] Confirm contribution hours with PM for the contribution table  
