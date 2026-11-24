# ADR-001: Sanitize and redact before any LLM call

- **Status:** Accepted  
- **Date:** 2026-11-24  
- **Owner:** Member 4 (Security & Governance)  
- **Deciders:** Member 4 (proposal), Member 1 (Core integration), Member 3 (AI consumer)  
- **Related reqs:** REQ-SEC-001, REQ-SEC-002, REQ-ARCH-004, INV-002, INV-004  
- **Enforcing code:** `src/security/sanitize.py`, `src/security/redact.py`  
- **Tests:** `test/offline/security/test_sanitize.py`, `test/offline/security/test_redact.py`

---

## Context

MedLeaveAssist sends free-text leave reasons and optional medical-document text into an LLM for **extraction only**. That path is safety-relevant:

1. Students (or compromised clients) can plant **prompt-injection** phrases that try to override policy (“ignore previous instructions”, “强制批准”).
2. Raw text may contain **PII** (student IDs, addresses) that must not leave the trust boundary into the model provider.
3. Course invariants forbid the AI from being the authority for eligibility; contaminated model input increases hallucination and policy-bypass risk.

Member 4 owns the security helpers; Core owns call order; AI owns extraction given already-cleaned text.

---

## Decision

Adopt a **mandatory pre-AI security pipeline**:

```
ApplicationPayload / document text
        │
        ▼
 sanitize_text / sanitize_application   (REQ-SEC-001)
        │
        ▼
 redact_pii / redact_for_llm            (REQ-SEC-002)
        │
        ▼
 AI extract(...)  only if Core sets ai_allowed after prechecks
```

Concrete rules:

1. **Sanitize first** — neutralize known injection / policy-override phrases (EN + ZH denylist) by replacing matches with `[FILTERED]`. Benign medical wording must survive.
2. **Redact second** — mask student IDs and address cues; **never** put `student_id` into the LLM-facing string; keep medical wording (e.g. diagnosis) when possible.
3. **Core gates the model** — AI extraction runs only after schema validation and security prechecks (`ai_allowed=True`). Failed validation must not call the model (REQ-ARCH-004).
4. **Do not extend `schemas.py`** for security DTOs; helpers return cleaned `ApplicationPayload`, plain strings, or package-local types.

---

## Alternatives considered

| Option | Summary | Why rejected / deferred |
|--------|---------|-------------------------|
| A. Trust the model / system prompt only | Rely on “you are an extractor” instructions | Injection can still override soft instructions; not deterministic; fails course safety boundary |
| B. Blocklist sanitize only, no PII redact | Filter injections but send raw IDs/addresses | Violates privacy / REQ-SEC-002; unnecessary provider exposure |
| C. Allowlist / structured forms only (no free text to LLM) | Students pick codes instead of free text | Better long-term, but breaks current FR (reason text + certificate extraction) |
| D. Full DLP / ML classifier before LLM | Enterprise content filter | Out of scope for coursework cost/complexity; denylist + redact is auditable and offline-testable |
| **E. Sanitize + redact helpers (chosen)** | Deterministic Python gates before AI | Matches invariants, offline tests, Member boundaries |

---

## Consequences

### Positive

- Deterministic, offline-testable security gates (27 Member-4 offline tests include adversarial cases).
- Clear authority split: security cleans; AI extracts; policy/human decide.
- Reduces accidental PII leakage into provider logs.
- Aligns with INV-002 (AI not authoritative) by shrinking the attack surface of the advisory path.

### Negative / tradeoffs

- Regex denylist is **not complete**; novel injection phrasings may pass → residual **guardrail debt** (track in `docs/debt-register.md`).
- Over-aggressive patterns could mangle rare legitimate text → monitor false positives in review packets.
- Until Core wires the helpers into `src/core/api.py`, production path may still bypass these gates (integration dependency on Member 1).

### Neutral

- Review routing, audit builders, and retention are **separate** ADRs / modules; this ADR only locks the pre-LLM input contract.

---

## AI context note (handoff to Member 3)

Per D2 ADR guidance, the model’s turn context must stay minimal and constrained. Under this decision, the **document/reason layer** the AI receives is only the **sanitized + redacted** string from `redact_for_llm` (plus Member 3’s static extraction prompt / schema).  

Full layered context assembly (identity, standing constraints, token budget, compaction, re-inject critical constraints) is owned in Member 3’s **Memory/State Design** and token-budget docs — those layers must **re-state** that extracted fields are advisory and never an approval decision.

---

## Reopen conditions

Revisit this ADR if any of the following occur:

1. A prompt-injection bypass reaches the model **and** alters downstream policy/review behavior in a demonstrated test.
2. Privacy review requires stronger DLP (names, HKID, phone) beyond student ID / address.
3. Product removes free-text-to-LLM and switches to structured OCR/forms (Option C).
4. Provider or campus policy mandates encryption / on-prem inference that changes the redact boundary.

---

## Verification checklist

- [x] Offline adversarial sanitize tests (EN + ZH)
- [x] Offline redact tests (ID + address; medical terms preserved)
- [x] `redact_for_llm` never includes `payload.student_id`
- [ ] Core apply/extract path calls sanitize → redact before AI (Member 1 integration)
- [ ] CI security path checks on PRs touching `src/security/` (Member 5)
