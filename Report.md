# MedLeaveAssist — CS5351 Agentic Software Engineering Project Report (D6)

**Course:** CS5351 Agentic Software Engineering  
**Project:** Campus Medical Leave Assistant (MedLeaveAssist)  
**Repository:** `CS5351-groupwork`  
**Document type:** Single consolidated process report (D6)  
**Assembled from:** `docs/drafts/report-m1.md` … `report-m5.md`  
**Consolidation owner:** Member 5 (PM)

---

## 1. Team roster and relative contribution

| Member | Name | Student ID | Role |
|--------|------|------------|------|
| 1 | Ma Jialin | 60213410 | Core & state machine; integration / consolidation |
| 2 | Feng Xinya | 60950980 | Rule engine & decision design |
| 3 | Yam Sin Yi | 60227960 | AI component & cost control |
| 4 | Mou Cheuk Hei | 56628433 | Security & governance |
| 5 | Tang Man Kit | 55641875 | QA, CI, PM; report consolidation |

### 1.1 Relative contribution table

Contribution weights follow the course example: mean productive effort = 1.0. Hours below are **team-agreed provisional estimates** for documentation of relative effort; the team may revise the hours column before final zip submission without changing the narrative chapters.

| Member | Sprint-style effort (hrs, provisional) | Relative contribution |
|--------|------------------------------------------:|----------------------:|
| Ma Jialin | 25 | 1.25 |
| Feng Xinya | 20 | 1.00 |
| Yam Sin Yi | 20 | 1.00 |
| Mou Cheuk Hei | 20 | 1.00 |
| Tang Man Kit | 15 | 0.75 |
| **Team mean** | **20** | **1.00** |

Relative contribution = member hours / team mean. Extreme free-rider adjustment was not required; all five roles delivered code and/or governance artifacts mapped in the trace matrix.

---

## 2. Project overview

MedLeaveAssist is a campus medical-leave workflow that accepts a student application (identity, course, date range, free-text reason, optional attachment reference), optionally extracts medical fields with an LLM, evaluates deterministic policy rules, and progresses a case through explicit statuses: `pending_docs`, `in_review`, `approved`, `rejected`, and `failed`.

The non-negotiable product red line is: **the LLM may extract facts but must never decide leave eligibility or write an approval.** Final approve/reject authority belongs to an authenticated counsellor on a case already in `in_review`, after deterministic policy constraints. Any incomplete, ambiguous, overlapping, or policy-failing path must fail closed or route to humans—never emit a false success.

The system is implemented as a FastAPI service with SQLite persistence, a YAML-configured rule engine, security helpers (sanitize / redact / access / retention), governance helpers (audit / review routing / review packets), and an advisory AI extraction package. Offline deterministic tests and a GitHub Actions `blocking-gate` workflow form the merge barrier. Live CityU model calls are opt-in and separated under `test/live/`.

### 2.1 Logical request path (authoritative write path)

At a high level, a successful apply request traverses the following stages. Stages in parentheses are advisory or gating helpers that must not invent an `approved` status:

```text
Client JSON
  → Pydantic ApplicationPayload validation (fail → 422)
  → sanitize_application (Member 4 helper; strips injection phrases)
  → redact_for_llm (Member 4 helper; strips student ID / address cues)
  → extract(...) if ai_allowed (Member 3; advisory ExtractionResult)
  → evaluate_policy(...) (Member 2; PolicyDecision)
  → map PolicyResult → CaseStatus (Member 1; never auto-approved on PASS alone)
  → optional governance route_decision escalation to in_review (never to approved)
  → persist CaseDB + extraction_json
  → SystemResponse with build_audit(...) metadata
```

Human approval is a separate authenticated review endpoint. This separation is the architectural expression of INV-001/INV-002: extraction and even “policy pass” are not sufficient to claim leave is granted.

### 2.2 Why an agentic process was required

The product contains a genuine AI component and a safety-relevant boundary. Without process controls, coding agents tend to “help” by collapsing that boundary—auto-approving high confidence extractions, writing status from the model, inventing token counts, or editing shared schemas to make tests green. The team therefore treated **process** (plans, ownership, CI, transcripts) as part of the product, not as paperwork after coding.

---

## 3. Software engineering process and how the team optimized it

### 3.1 Process model

The team used a supervised agentic lifecycle aligned with course deliverables D1–D9:

1. **Machine-readable requirements** (`docs/req/requirements.yaml`) with Fit Criteria.  
2. **Architecture constraints** under `docs/architecture/` (invariants, trace matrix, permission model, ADRs, memory/token notes, runtime policy).  
3. **Coding governance** via `AGENTS.md`, `.opencode/`, and `.agent/rules.md`: plan → human approve → code → offline verify.  
4. **Module ownership** so five members and their coding agents could work in parallel without rewriting shared contracts (`src/schemas.py` frozen).  
5. **Verification governance**: offline suites, CI blocking gates, review memos, debt and bug diaries.  
6. **Annotated agent transcripts** (D5) recording human interrupts.  
7. **Single process report** (this document) plus contribution weights.

### 3.2 Optimizations adopted during the project

| Problem observed | Process optimization |
|------------------|----------------------|
| Agents tried to edit `schemas.py` or foreign modules | Hard path whitelist in `AGENTS.md` / permission model; humans rejected out-of-scope plans |
| Early “pass → approved” shortcuts | Invariants + negative tests; Core maps policy `PASS` to `pending_docs`, not auto-approve |
| Docs colliding on `main` | Feature/docs branches + protected `main` (PR-only); drafts isolated under `docs/drafts/report-m*.md` |
| Soft CI that could not prove a break | Replaced ad-hoc pytest with named `blocking-gate` (Gate A/B/C) and a negative-control drill |
| Provider APIs incompatible with first AI adapter | Fail-closed production CityU path; experimental Chat Completions kept under `test/live/` without inventing token counts |
| Late integration risk | Staged merges; Core later wired sanitize → redact → AI → route/audit so security helpers are on the write path |

### 3.3 Tooling pattern

Members used Cursor and/or OpenCode. The shared discipline was identical: the agent drafts; the human owns authority (approve plan, reject schema edits, refuse fake success, refuse fabricated metrics). Transcripts document interrupts such as rejecting auto-approve routing, rejecting destructive retention deletes from the security module, and correcting priority / teaching-day semantics in the rule engine.

### 3.4 Sprint-like working rhythm

Although the course did not mandate formal Scrum ceremonies, the team converged on a repeatable mini-cycle for each owned module:

1. Read `AGENTS.md` and the relevant requirement IDs.  
2. Produce an execution plan (interfaces, negatives, non-goals) and stop for human approval.  
3. Implement inside the owned directory only; add offline tests in the same change.  
4. Run module tests, then a wider offline subset when touching shared paths.  
5. Open a PR against `main` (never direct push to the protected branch).  
6. Update or reference architecture/trace/debt artifacts when behaviour or Fit Criteria changed.  
7. Record human interventions in the member transcript for D5 evidence.

This rhythm reduced “agent completes the whole system unattended” failure mode and made late integration (security wiring, CI gate hardening, report consolidation) predictable enough to schedule explicitly.

### 3.5 Communication and conflict handling

Conflicts were mostly technical rather than interpersonal: schema ownership, who may edit `ci.yml` / trace matrix, how to interpret CityU token APIs, and whether security helpers counted before Core called them. The team resolved these by writing the decision down (ADR, AGENTS.md note, debt register, or PR description) instead of leaving contradictory oral agreements. When GitHub rejected a direct `main` push, the process reminder was mechanical and unambiguous: use a feature/docs branch and a pull request. When a trace pointer file disappeared, regeneration plus Gate C re-check restored the evidence chain quickly.

---

## 4. Process quality evidence

### 4.1 Requirement volatility

Core product invariants remained stable throughout: AI is advisory only; no fake success; deterministic policy; auditable decisions. Volatility concentrated on **implementation Fit Criteria** rather than rewriting the red line:

- **Short-leave threshold:** rule condition corrected from `< 2` to `<= 2` teaching days after valid two-day cases failed closed.  
- **Duration semantics:** calendar days → Monday–Friday teaching days for consecutive-leave rules (REQ-FR-007).  
- **Provider / token accounting:** CityU rejected some count and structured-output routes; requirements stayed “fail closed if budget unverifiable,” which left production CityU generation incomplete by design rather than silently faking counts.  
- **Trace / ownership:** `ci.yml` and trace-matrix ownership notes moved as PM and Core coordinated late-stage governance; the root trace pointer was regenerated after accidental deletion (2026-11-25) and re-verified.

### 4.2 Defect trends (selected)

Defects were tracked narratively in member chapters and `docs/bug-diary.md` rather than as a formal weekly rate chart. Representative trend:

| Phase | Typical defects | Trend after fix |
|-------|-----------------|-----------------|
| Scaffold / contract | Import paths, schema temptation | Stabilized once schemas frozen |
| Policy config | Priority direction, teaching-day count, `None` comparison leak | Offline policy suite expanded; fail-closed wrappers |
| Local runtime | Stale SQLite missing `extraction_json`; YAML prompt loaded as JSON | Documented reset; loader accepts YAML/JSON |
| AI provider | HTTP 400/405 on preferred interfaces | Fail-closed preflight; live experiments separated |
| Security helpers | Over-greedy address regex swallowing diagnosis | Pattern + adversarial tests |
| Integration | Security helpers not initially called from Core | Wired into `/api/apply` before final consolidation; live wire check added |

Overall, defect class shifted from “wrong architecture shortcuts” early to “provider/environment and integration plumbing” late—an expected pattern when invariants are enforced early.

### 4.3 Ambiguity resolution

Ambiguities were resolved by written contracts and human decisions, not by letting the model invent policy:

- **Who may approve?** Only counsellor review API after `in_review`.  
- **What is a token count?** Provider-reported usage after generation ≠ verified preflight budget; incomplete CityU preflight remains empty extraction.  
- **Who owns purge?** Security returns `should_purge`; Core/ops owns destructive delete.  
- **What is “priority” in YAML?** Larger number wins; caught before coding shipped inverted semantics.  
- **PR vs push to `main`?** Branch protection requires PRs; `origin/` prefix is remote-tracking display, not a second branch type.

### 4.4 Artifact co-evolution

When code or rules changed, the team updated linked artifacts in the same sprint where possible:

- Rule YAML ↔ policy tests ↔ runtime-policy notes ↔ Fit Criteria in `requirements.yaml`.  
- Prompt `prompt_v1.0.yaml` ↔ extractor loader ↔ CI prompt metadata gate.  
- Security ADRs / permission model ↔ security offline tests ↔ Core apply wiring + live wire test.  
- Trace matrix ↔ Gate C existence checks; regenerated pointer after accidental delete.  
- Member report drafts under `docs/drafts/` co-evolved with modules, then merged into this `Report.md`.

Human oversight explicitly blocked agents from “updating everything” by rewriting foreign modules; co-evolution was coordinated through PRs and ownership tables instead.

### 4.5 What human oversight caught that agents did not

Examples recorded in D5 transcripts and member reflections:

- Rejecting agent proposals to modify `schemas.py` for convenience.  
- Rejecting `pass → approved` and governance `recommended_status=APPROVED`.  
- Rejecting fabricated preflight token counts to “complete” REQ-COST-001.  
- Catching inverted rule priority and calendar-vs-teaching-day bugs before/during test writing.  
- Catching a live evaluator that could print failed comparisons without failing pytest.  
- Catching greedy PII regex damage to medical text.  
- Enforcing PR-only merges after direct `main` pushes were rejected by GitHub protection.

---

## 5. Core link and state machine (Member 1)

### 5.1 Role and authority boundary

Member 1 owns the core FastAPI workflow service, SQLite persistence layer, deterministic rule-evaluation integration, repository integration, and cross-member/agent governance covering REQ-FR-001, REQ-FR-002, REQ-FR-003, REQ-FR-005, REQ-FR-006, REQ-FR-007, REQ-INV-001, REQ-INV-003, REQ-INV-005, REQ-ARCH-002, REQ-COST-001, and REQ-PER-001. Member 1 also coordinates late-stage branch synchronization, teammate PR review, directory/traceability alignment, and final repository consolidation.

Core workflow endpoints (`/api/apply`, `/api/status/{case_id}`, `/api/apply/{case_id}/supplement`, `/api/review/{case_id}/decision`) manage case lifecycle transitions and persist structured extraction results together with audit records. The core path enforces deterministic state progression, duplicate `case_id` rejection (`409 Conflict`), counsellor token verification (`x-counselor-token`), and fail-closed fallback routing. Model outputs are treated strictly as untrusted or advisory inputs rather than final decision or approval authority.

### 5.2 State machine, policy evaluation, and fail-closed behaviour

The medical-leave workflow tracks applications across explicit states (`pending_docs`, `in_review`, `approved`, `rejected`, `failed`) while recording audit metadata such as actor, rule version, model version, and prompt version. Policy evaluation consumes configurable rule definitions and checks leave duration, date ordering/validity, overlap with previously approved leave, and required supporting evidence deterministically instead of delegating approval choices to an LLM.

Whenever input payloads are incomplete, ambiguous, conflicting, or fail policy and validation constraints, the system routes cases to `pending_docs` or `in_review`, or fails closed (`failed`) rather than emitting a false-positive approval. Final approval requires an explicit authorized reviewer decision on a case in `in_review` accompanied by a valid counsellor token. Offline/no-op execution avoids external model calls while preserving safe routing behaviour.

### 5.3 Defects resolved and local runtime debugging

End-to-end integration and local runtime testing surfaced three concrete issues across prompt loading, policy configuration, and database state:

1. **Prompt configuration loading:** Loading `prompts/prompt_v1.0.yaml` previously triggered `JSONDecodeError` when parsed strictly as JSON. Updating the loader to support YAML/JSON parsing enabled versioned prompt metadata to load cleanly without breaking local execution or offline tests.  
2. **Short-leave rule threshold:** The short-leave rule previously evaluated `< 2` teaching days rather than `<= 2` teaching days, causing valid 2-day medical-leave submissions to miss the rule and fail closed. Updating the threshold to `<= 2` days restored expected handling while preserving mandatory human review and counsellor approval checks.  
3. **Stale local SQLite schema (`medleave.db`):** Running uvicorn and submitting `POST /api/apply` initially failed with `sqlite3.OperationalError: no such column: cases.extraction_json` because an earlier local database file lacked the newer column. Removing the stale file and recreating tables from the current schema allowed the full Apply → Status → Supplement → Review lifecycle (`pending_docs` → `in_review` → `approved`) to pass end-to-end in local PowerShell tests.

### 5.4 Cross-member review, security wiring, and final integration governance

To keep parallel work across five teammates and multiple AI coding agents from colliding near the deadline, Member 1 put path and verification guardrails in place via `.opencode/rules.md`, `.gitignore`, and the trace matrix. Teammate report drafts were isolated under `docs/drafts/report-m*.md`, architecture/ADR notes under `docs/architecture/`, and session transcripts under `transcripts/`. Shared schemas (`src/schemas.py`) and CI blocking gates were protected against unauthorized edits.

Rather than forcing repeated partial merges while teammates were still updating documentation and module branches, Member 1 reviewed incoming PR diffs for scope and requirement alignment, verified offline test and traceability gates, and planned final branch synchronization once remaining member PRs settled on `main`.

A critical late integration step was wiring Member 4’s security and governance helpers into the authoritative apply path: `sanitize_application` → `redact_for_llm` → AI `extract` → policy evaluation → cautious governance review routing → `build_audit`. Empty or skipped AI results do not force `in_review` solely via null low-confidence fields (preserving short-leave `pending_docs` behaviour), and `FAIL_CLOSED` remains `failed`. This closed the earlier honesty gap where security helpers passed unit tests but were not yet invoked by Core.

### 5.5 Limitations and next steps

Current limitations include manual local `.db` file reset during schema changes rather than automated migration tooling, residual transcript/requirement path cleanup across late branches, and reliance on local/offline verification for most scenarios (with selective opt-in live checks). Next steps for a production hardening pass would include automated migrations, durable access-log persistence, and broader live-gateway regression beyond the experimental packages.

---

## 6. Rule engine and decision design (Member 2)

Leave decisions in MedLeaveAssist are made entirely by a deterministic rule engine; AI never participates in any approval decision. The engine exposes `evaluate_policy(payload) -> PolicyDecision` as its contract and loads rules dynamically from `policy_v1.0.yaml`, achieving “change rules without changing code” (REQ-FR-003).

### 6.1 Four-layer design

1. **Data model** — `Rule` / `RuleSet` dataclasses whose fields align with `PolicyDecision`; `action` strictly uses the `PolicyResult` enum, forbidding magic strings.  
2. **Safe condition evaluator** — an `ast` whitelist walker (no `eval`/`exec`/`compile`) that only allows boolean/comparison/name/constant nodes; any call, attribute access, subscript, or power operation is rejected; length and node-count limits guard against DoS (aligned with input-boundary safety).  
3. **Strict loader** — validates every field; missing fields, invalid actions, typos, and `bool` masquerading as `int` all fail closed; the rule set is cached by resolved absolute path.  
4. **Decision engine** — iterates in descending priority (larger number first), short-circuits immediately on a `fail-closed` hit; otherwise aggregates with `route-to-review` winning over `pass`.

### 6.2 Key safety properties

- All exceptions are caught and converted to `fail-closed`; the engine never raises and never returns a fake success (REQ-INV-001); no rule matched means default-deny.  
- The same input produces identical results across repeated runs (REQ-INV-005); no `datetime.now()` is used inside decision evaluation.  
- A single decision takes on the order of ~0.04 ms, far below p95 < 500 ms (REQ-PER-001).  
- For REQ-FR-007 “consecutive teaching days” semantics, `duration_days` counts only Monday–Friday, preventing a Friday→Monday range from being miscounted as four calendar days.

### 6.3 Verification

The implementation is backed by a large offline suite covering normal paths, boundaries (weekends, invalid dates), and injection-attack negatives (`__import__`, attribute access, power bombs, unknown variables, type mismatches). Human review caught inverted priority semantics and calendar-vs-teaching-day ambiguity before those mistakes could silently weaken overlap or long-leave protections.

---

## 7. AI component and cost optimization (Member 3)

### 7.1 Role and authority boundary

Member 3 owns the AI extraction, student guidance, counsellor-summary, and application token-control components for REQ-FR-002, REQ-FR-005, REQ-FR-006, REQ-INV-002, REQ-INV-004, and REQ-COST-001. The extractor returns advisory medical facts through the shared `ExtractionResult` Pydantic contract. It has no authority to determine eligibility, make the policy decision, route a final case, or write an approval/rejection state. Those actions belong to deterministic policy, core workflow, or authorized human review.

### 7.2 Extraction, prompt, and factual validation

The versioned extraction prompt requests hospital name, consultation date, recommended rest duration, and diagnosis. It treats the supplied certificate text as untrusted evidence, forbids eligibility decisions and unsupported inference, and requests `null` for missing or ambiguous facts. Each field carries `derived=True` and a confidence value.

The application validates the response locally rather than trusting prompt instructions alone. The decoder rejects malformed JSON, duplicate or unexpected keys, wrong field types, invalid confidence values, and fields without the required derived marker. A second source-grounding check accepts a value only when it matches the unique value on a supported labelled source line; dates must be valid ISO dates and the `Issue date` label is not treated as a visit date. Unsupported or ambiguous values are cleared, and low-confidence values are not returned as usable facts. The `confidence` number is model-reported and is not a calibrated accuracy guarantee.

The validator is intentionally conservative: it does not yet support arbitrary certificate layouts, every date format, image/PDF extraction, or document-authenticity verification. Those require separately reviewed preprocessing and validation. Security/core callers must authorize access, sanitize and redact text, and meet the provider’s data-handling requirements before model invocation.

### 7.3 Guidance and summaries

Student-facing missing-material guidance and counsellor summaries use deterministic templates, avoiding extra LLM requests for these functions. Guidance is constructed from a caller-provided `PolicyDecision`, its actual missing items, and fired rule IDs. The summary formats explicitly supplied display name, duration, dates, derived diagnosis, and document-completeness status; it does not infer completeness or recommend approval. End-to-end invocation, display authorization, audit persistence, and status transitions remain integration responsibilities owned with Core and governance.

### 7.4 Cost strategy and provider compatibility

REQ-COST-001 sets an average target of at most 1,500 tokens per request, a 3,000-token total hard limit, and no model call for eligible simple requests. For a supported provider, the extraction path reserves 300 output tokens and permits generation only when an input-token count for the complete request plus that output reserve is at most 3,000. It fails closed on unavailable, invalid, or oversized preflight counts, and checks provider-reported usage after generation. The latter is a consistency check; it cannot prevent already-consumed tokens. Simple-request eligibility is supplied by the caller.

The CityU gateway accepted the tested Chat Completions route, but rejected strict JSON Schema response formatting with HTTP 400. Two tested token-count routes returned HTTP 405. No exact or defensible count for this model alias and complete chat framing has been verified for production preflight. Consequently the ordinary CityU extraction path fail-closes during preflight and returns empty derived fields without generation. This is a deliberately fail-closed, **incomplete production integration**; REQ-COST-001 is not claimed complete for this provider. No character/byte proxy or mock count is represented as a real production token count.

### 7.5 Verification evidence and limitations

All 37 Member 3 AI offline tests passed using mocks at the reviewed baseline. These cover the contract, missing/conflicting or unsupported fields, grounding, low confidence, malformed responses, skipped requests, preflight budget branches, errors, and the CityU adapter’s blocked preflight. The live-test package was separately verified to collect and, under opt-in credentials, to execute experimental cases.

An earlier experimental evaluation used five synthetic labelled-text certificates via direct experimental generation rather than the production preflight path. Provider-reported total usage averaged about **347.2** tokens across those five cases (maximum 360). These results are historical evidence for a small set, not a population-wide average or proof that the production 3,000-token hard cap works for every future request.

Code review identified limitations in the historical five-case evaluator: it could print expected-value comparisons without asserting overall pass/fail at the end, its validation helper omitted some production low-confidence filtering, and failed attempts could read stale experimental usage metadata. These gaps remain honestly reported. Holding text temporarily does not prove secure deletion, and returning an extraction does not prove that it was persisted or audited correctly—those remain Core/security responsibilities.

---

## 8. Security boundaries and data compliance (Member 4)

### 8.1 Why this boundary exists

MedLeaveAssist uses an LLM only to **extract** fields from leave reasons and medical text. Eligibility and approval must stay with **deterministic policy code** and **human counsellors**. That split creates a hard security/governance boundary: anything that reaches the model, anything that reaches an advisor’s screen, and anything that can change case status must be constrained so the team cannot ship a “fake success” or leak student identity to a model provider.

Member 4 owns two packages that encode this boundary without owning the Core write path:

| Package | Responsibility |
|---------|----------------|
| `src/security/` | Sanitize free text, redact PII, least-privilege access checks, retention decision helper |
| `src/governance/` | Audit metadata, review routing advice, human-review evidence packets, sensitive-access logging |

Architecture decisions are recorded in ADR-001 (sanitize → redact before LLM) and ADR-002 (governance never recommends `approved`). File-level agent rights and runtime roles are in `docs/architecture/permission-model.md`.

### 8.2 Pre-AI input gate (REQ-SEC-001 / REQ-SEC-002)

**Threat.** Free-text fields can carry prompt-injection and policy-override language (“ignore previous instructions”, “强制批准”). The same fields may embed student IDs and addresses that must not leave the campus trust boundary.

**Control.**

1. `sanitize_text` / `sanitize_application` replace known EN/ZH injection patterns with `[FILTERED]` before downstream use.  
2. `redact_pii` / `redact_for_llm` mask IDs and address cues, omit `student_id` from the LLM-facing string, and try to preserve medical wording (e.g. stop address redaction before a `诊断` / `diagnosis` label).

**Call order:** validate payload → sanitize → redact → (only then) AI extract if `ai_allowed`. This matches REQ-ARCH-004 and ADR-001. Evidence: `test/offline/security/test_sanitize.py`, `test_redact.py`.

### 8.3 Least privilege, access logging, retention (REQ-SEC-003 / REQ-SEC-004)

Runtime roles (`src/security/access.py`): `student` may view raw medical content only for own case; `advisor` / `admin` allowed; unknown roles denied (`AccessDenied`). Authorized sensitive opens should record `case_id`, `actor_id`, `role`, `action`, and UTC timestamp. Retention helper `should_purge` returns true when `now >= closed_at + 30 days`; destructive deletion remains Core/ops so a coding agent cannot wipe production rows from the security module.

### 8.4 Governance: audit, routing, anti rubber-stamp (REQ-GOV-001…004)

`build_audit` requires non-empty `actor` and `rule_version`, with optional model/prompt versions (INV-005). `route_decision` sends low-confidence extraction, missing documents, red flags, and policy route/fail-closed/overlap signals toward human review and **never** recommends `CaseStatus.APPROVED`. `build_review_packet` exposes evidence snippets, derived fields with exact values + `derived` + `confidence`, policy summary, and action flags (`challenge_allowed`, `escalate_allowed`, `approve_requires_explicit_ack`).

### 8.5 Authority map

| Actor / component | May advise | May decide approve/reject | Notes |
|-------------------|:----------:|:-------------------------:|-------|
| LLM extraction | Yes | No | Advisory `ExtractionResult` only |
| Security sanitize/redact | Gate inputs | No | Mandatory before AI |
| Governance router / packet | Yes (`in_review`) | No | Never recommends `approved` |
| Policy engine | Pass / fail-closed / route | Constrains Core | Deterministic rules |
| Human counsellor via Core | — | Yes | Sole approval authority after review gates |

### 8.6 Residual risk, debt, and integration status

| Residual risk | Mitigation / debt |
|---------------|-------------------|
| Regex denylist will miss novel injections | Guardrail debt; expand patterns from bug-diary incidents |
| In-memory access log | Must move to durable store before production claims |
| Over-routing if confidence threshold is low | Tune with Members 1/2 using review backlog metrics |

Offline suites under `test/offline/security` and `test/offline/governance` reported **27 passed**. After Core wiring, offline API tests including `test_apply_sanitizes_and_redacts_before_ai` passed, and an opt-in live test (`test/live/test_core_secgov_wire_live.py`) confirmed that injection phrases and student IDs did not reach the CityU provider document while audit metadata remained populated and status was never `approved`.

---

## 9. QA, CI blocking gate, and governance traceability (Member 5)

### 9.1 Role and authority boundary

Member 5 owns REQ-ARCH-002 (low coupling between Extractor, Policy Engine and Summarizer), REQ-GOV-005 (prompt versioning and code rules), REQ-GOV-006 (CI blocking gate) and REQ-GOV-007 (traceability). Member 5 also recorded the REQ-QUAL-002 conflict priority in `AGENTS.md`: reliability, then input-boundary safety, then accountability, then cost.

Member 5 did not own policy decisions, AI extraction, sanitization, or the authoritative status write path. Deliverables are verification artifacts: tests that fail when a contract or governance rule is broken, a CI job that makes failures non-mergeable, and records that make the evidence reviewable. The coding agent could draft these artifacts only after explicit human approval; it never had merge authority. As PM, Member 5 consolidates this `Report.md` from member drafts.

### 9.2 CI blocking gate design

The original workflow ran a single `pytest test/offline/ -v` command. It had no stable required status check name, insufficient governance checks, and weak proof that a deliberate break would block a merge. It was replaced by one job named `blocking-gate`:

```text
PR / push to main
   |
   v
Gate A - governance static checks   (test_ci_governance.py)
Gate B - full offline suite          (test/offline)
Gate C - trace matrix coverage       (test_trace_matrix.py)
   |
   v
Any failure -> job fails -> GitHub rejects merge
```

A YAML self-check test parses the workflow and rejects `continue-on-error`, `|| true`, renamed jobs, removed pytest steps, and conditional skips on test steps. The only `if: always()` step is the JUnit evidence upload, which does not affect the verdict. The job name `blocking-gate` must remain a required status check on `main`. Configuration guidance is in `docs/ci-gate.md`.

### 9.3 Static governance enforcement

Gate A inspects source files with AST parsing instead of importing them:

- `import sqlite3`, raw SQL string literals, `execute()` with a SQL literal, `sqlalchemy.text()` and raw `cursor()` are forbidden; database modules must import SQLAlchemy ORM.  
- `src/ai/` may not import `src/policy/`, and `src/policy/` may not import `src/ai/` (machine-checkable REQ-ARCH-002).  
- AI modules may not emit `CaseStatus.APPROVED` or an `approved` literal, reinforcing REQ-ARCH-001 and REQ-INV-002.  
- `prompts/prompt_v1.0.yaml` must exist, parse, contain required metadata, match its filename version, and declare extraction-only authority.

These checks are deterministic and offline; they make no model call.

### 9.4 Contract and integration evidence

`src/schemas.py` was treated as a frozen contract. Contract tests assert exact field sets for `ApplicationPayload`, `ExtractionResult`, `ExtractedField`, `PolicyDecision`, `AuditInfo` and `SystemResponse`, plus closed enum values. Fabricated sick-leave JSON with an invalid date, a missing `reason_text` and an extra `approved` flag must raise `ValidationError`.

Integration tests use mock policy rather than editing Member 1 or Member 2 modules. They cover apply, status, supplement, review queue and authenticated decision, and assert that no `approved` state appears without an authorized human review.

A negative-control drill temporarily injected a fabricated failing test and produced a non-zero exit code while the remainder of the suite stayed intact; the temporary file was removed and the suite re-verified green. This is Fit Criterion evidence for REQ-GOV-006: a deliberate break really can block the PR.

### 9.5 Traceability and governance records

`docs/trace-matrix.md` maps requirement IDs (FR, INV, ARCH, SEC, COST, PERF, QUAL, GOV) to code references and test references. Gate C checks completeness, duplicate IDs and the existence of referenced test files. The root trace pointer was accidentally deleted by a team member on 2026-11-25, regenerated, and re-verified—an example of artifact co-evolution under time pressure.

The M5 record set includes `docs/code-governance/verification-constraints.md`, `docs/review-memo.md`, `docs/debt-register.md`, `docs/bug-diary.md`, `.opencode/permissions.jsonc`, `.agent/rules.md`, and the D5 transcript `transcripts/55641875-Tang Man Kit.md`.

### 9.6 Residual risk and debt

Open items recorded in `docs/debt-register.md` include confirming branch protection remains enabled, placeholder prompt `model_version` where applicable, pending trace-matrix rows, and ownership of SSO / token metering / p95 benchmarks by other roles. Line-ending-only git noise from `core.autocrlf` is noted so reviewers do not confuse it with substantive churn. These are reported, not hidden.

---

## 10. Deliverables map (D1–D9) and how process evidence is stored

| ID | Deliverable | Where it lives in this repository | Primary owners |
|----|-------------|-----------------------------------|----------------|
| D1 | Machine-readable requirements | `docs/req/requirements.yaml`, schema validation artifacts | Team; Fit Criteria contributions from Members 1–2 |
| D2 | Architecture artifacts | `docs/architecture/` (invariants, trace matrix, permission model, ADRs, memory/token, runtime policy, …) | Split by role (M1 invariants/trace; M2 runtime policy; M3 memory/token; M4 permission/ADR; …) |
| D3 | Coding governance | `AGENTS.md`, `.opencode/`, `.agent/rules.md`, structural constraints | M5 final review; all members obey |
| D4 | Verification governance | `verification-constraints.md`, `review-memo.md`, `debt-register.md`, `bug-diary.md` | M5 |
| D5 | Annotated agent transcripts | `transcripts/<student-id>-<name>.md` | Each member |
| D6 | Process report + reflections | This file: `Report.md` | M5 consolidates; chapters from M1–M5 drafts |
| D7 | GitHub CI + protected `main` | `.github/workflows/ci.yml`, branch protection | M5 design; admin enablement |
| D8 | Source and tests | `src/`, `test/offline/`, `test/live/` | All module owners |
| D9 | Static startup prompt | `Prompt.md` (and runtime prompts under `prompts/`) | Team governance |

This mapping is itself process evidence: when a requirement or module changed, the team could point to the corresponding D-artifact that must be updated. Failures to update (for example a missing trace pointer) became visible through Gate C rather than only during final packaging.

---

## 11. Verification snapshot (end-to-end readiness)

| Layer | Evidence (representative) |
|-------|---------------------------|
| Offline suite | Full `pytest test/offline` green after Core sec/gov wiring (110+ tests in late local runs) |
| Security/governance unit | 27 passed |
| AI offline | 37 passed (Member 3 baseline) |
| Policy offline | Large deterministic suite including adversarial conditions |
| CI | `blocking-gate` Gates A/B/C |
| Live (opt-in) | CityU single-case extraction passed; Core wire live test passed (sanitize/redact/audit; status ≠ approved) |

### 11.1 How to run verification (for auditors)

Offline (default, CI):

```text
pip install -r requirements.txt
pytest test/offline -q
```

Live (opt-in; requires external credentials outside the repo):

```text
set RUN_AZURE_LIVE=1
pytest test/live/ai/test_member3_live_cityu.py -v -s
pytest test/live/test_core_secgov_wire_live.py -v -s
```

Credentials are loaded from the operator’s private `~/CS5351/Project/agent.env` and must never be committed. Live success on a small synthetic set does not replace the offline blocking suite.

Remaining honesty items: not every E2E scenario is live-gateway verified; CityU production preflight remains fail-closed for unverified token counting; some governance persistence (access log) is still in-memory; a subset of trace-matrix rows may still be marked pending pending owner updates.

---

## 12. Individual self-reflections

### 12.1 Ma Jialin (60213410) — Member 1

As Member 1 of MedLeaveAssist, I was responsible for the core backend workflow, deterministic policy integration, repository integration, cross-team governance, and final consolidation. Working through this project made it clear that using AI coding agents effectively requires disciplined engineering guardrails—clear scope boundaries, careful diff inspection, and deterministic verification—rather than accepting generated output at face value. CLI coding agents accelerated repository exploration, test inspection, and drafting, while human review remained essential to protect shared contracts, invariants, and test gates.

Integrating multiple components also showed how small mismatches between configuration, policy rules, and local runtime state can disrupt an end-to-end flow. Encountering a `JSONDecodeError` on YAML prompt loading, a `< 2` versus `<= 2` day short-leave threshold, and a `no such column: cases.extraction_json` error from a stale local `medleave.db` file highlighted the value of tracing each failure to its root cause and verifying that fixes keep fail-closed and counsellor-authorization invariants intact.

Managing integration and final alignment across five team members underscored the importance of lightweight coordination and honest reporting of both progress and gaps. Isolating individual drafts, reviewing teammate PRs for unintended edits or requirement drift, and timing final branch consolidation around upstream PR completion helped avoid unnecessary merge churn. If I were to repeat this project, I would standardize transcript folder naming, requirement-to-file references, and local database reset/migration notes earlier so final integration requires minimal cleanup. Overall, my contribution focused on keeping the core workflow reliable, traceable, and cohesive while bringing the team's deliverables together into a well-aligned final submission.

### 12.2 Feng Xinya (60950980) — Member 2

Building the rule engine taught me that “deterministic” is a design discipline, not a single function call. My biggest early mistake was a semantic one: I wrote “smaller priority number = higher priority” while the assigned values (1000 for overlap) clearly meant the opposite. Catching that contradiction before writing code prevented the short-leave rule from silently shadowing critical blocks—a reminder that requirements and their numbers must be reconciled, not just copied.

The second lesson was about security by construction. Instead of trusting YAML expressions, I built an AST whitelist evaluator that forbids calls, attribute access, and even exponentiation, so a malicious condition cannot execute code. A later self-audit found that `None < int` raised a raw `TypeError` that would have bypassed fail-closed handling; wrapping comparisons turned a subtle leak into a clean configuration error. This reinforced that fail-closed must be verified at every boundary, not assumed.

Configuration over hardcoding was the core architectural win. Every threshold and action lives in YAML, and the loader strictly rejects typos, invalid actions, and missing fields, letting non-developers adjust policy without risking code changes. Finally, the requirements audit was humbling: my initial `duration_days` counted calendar days, which violated consecutive teaching-day semantics. I fixed it to exclude weekends and realigned all tests. I also learned to draw clear module boundaries—overlap detection and explanation-with-rule-ID depend on API/DB layers—so I documented handover tasks rather than overreaching. The plan → approve → code workflow enforced by `AGENTS.md` kept changes reviewable and prevented scope creep.

### 12.3 Yam Sin Yi (60227960) — Member 3

As Member 3 of MedLeaveAssist, I was responsible for medical-information extraction, student guidance, counsellor summaries, and token-control components. This project helped me understand that effective AI-assisted development requires a controlled engineering process rather than simply generating working code. I used Cursor and OpenCode within a plan-and-approval workflow, reviewed proposed changes, and restricted modifications to my assigned paths to protect the shared schema and teammates’ modules. The main requirements remained stable: AI could extract information but could not approve leave, determine eligibility, or invent medical facts. Nevertheless, implementation exposed ambiguities concerning provider compatibility, evidence validation, and token accounting. The CityU gateway rejected interfaces used by the original adapter, whereas an experimental Chat Completions path successfully returned JSON. This required adapting the technical approach while preserving the original authority boundaries.

Another important clarification concerned the difference between measuring tokens after generation and enforcing a budget before sending a request. Five synthetic cases reported an average of about 347 tokens, but this small sample could not demonstrate that every future request would remain below the 3,000-token limit. The review process rejected fabricated preflight counts and retained fail-closed behaviour in the production CityU path, even though this left integration incomplete. Testing provided evidence of progress while revealing the limits of automated verification. The AI offline suite expanded after CityU adapter tests were added, covering blocked preflight and failure paths, yet increased coverage did not establish general model accuracy because no formal defect-rate trend had been recorded. Reviewing the live evaluator also revealed that it could print a failed extraction comparison without making pytest fail—demonstrating why human review must inspect assertions rather than trust a green printout. To keep artifacts aligned, I distinguished historical experimental evidence from production claims, kept the shared data contract unchanged, and left cross-module consolidation to Member 1. Overall, this experience showed that responsible use of coding agents depends on human judgement about requirements, assumptions, and evidence.

### 12.4 Mou Cheuk Hei (56628433) — Member 4

Working as Security & Governance owner taught me that in an agentic project the hardest part is not writing another helper function—it is stopping the agent and teammates from optimizing away the safety boundary. Early plans from the coding agent repeatedly drifted toward editing `schemas.py`, auto-approving high-confidence cases, or deleting database rows from the retention module. Each time, the useful move was the same: point at `AGENTS.md` and the invariants, reject the change, and ask for a narrower plan that stayed inside `src/security` and `src/governance`.

I also learned to treat tests as the real specification. Adversarial sanitize cases in English and Chinese, redaction cases that must keep diagnosis text, and `test_router_never_recommends_approved` matter more than a prose claim that we are “secure.” When a greedy address regex swallowed the medical clause, the failing intended example forced a better pattern; that debugging loop felt closer to real security engineering than adding more comments.

Coordination was as important as code. ADR-001 and the permission model make an explicit handoff: I provide gates; Member 1 owns call order; Member 3 consumes only cleaned text; Member 5 gates safety paths in CI. Until Core wired sanitize and redact, our controls were correct in isolation but not yet enforced on the live apply path—an honest gap we closed late and verified with offline plus opt-in live wire tests. Finally, using Cursor under human approval changed how I supervise AI: plan only first, refuse schema and foreign-module edits by default, and annotate interventions for the transcript. The agent is fast at scaffolding; the human is responsible for authority—what may never be approved, what may never be sent to the model, and what may never be written by the wrong role.

### 12.5 Tang Man Kit (55641875) — Member 5

As Member 5 of MedLeaveAssist, I was responsible for quality assurance, the CI/CD blocking gate, testing support, the traceability matrix, governance records, and report consolidation as PM. This project showed me that effective AI-assisted development depends less on generating files quickly and more on controlling what the agent may change. I used OpenCode within a plan-and-approval workflow to produce the CI blocking gate and related verification code, and I restricted modifications to assigned paths so that `src/schemas.py`, teammates’ authoritative modules, and red-line contracts stayed protected unless ownership explicitly moved.

Building a gate that can turn red on purpose—and proving it with a negative-control drill—mattered more to me than adding decorative dashboards. Traceability work also taught me that documents rot unless CI checks file existence and ID completeness; regenerating a deleted pointer under time pressure reinforced that governance artifacts are part of the product, not optional homework. Consolidating five report drafts into one D6 document required preserving each member’s technical voice while adding the shared process story the rubric demands: volatility, defects, ambiguity resolution, co-evolution, and human overrides of agents.

In future work I would define negative-test acceptance criteria earlier, preserve full agent transcripts from day one, and coordinate integration checkpoints on a fixed calendar rather than near the deadline. Responsible use of coding agents depends on human judgement about requirements and assumptions; my main contribution was making quality failures non-mergeable and making the team’s evidence reviewable in one report.

---

## 13. Cross-cutting lessons learned (team synthesis)

Beyond individual reflections, the team converged on several shared lessons that future agentic projects should treat as defaults:

1. **Authority is a first-class design artifact.** Every module must answer: may this code advise, constrain, or decide? Mixing those verbs is how “helpful” agents create false success.  
2. **Frozen contracts beat clever regenerations.** Keeping `schemas.py` stable forced adapters and helpers to meet the contract instead of mutating it under schedule pressure.  
3. **Fail closed is a test obligation.** It is not enough to write a comment saying the system fails closed; negative tests and CI gates must turn red when someone disables the fail path.  
4. **Provider reality can break beautiful designs.** Token preflight and structured-output assumptions failed against CityU; the correct engineering response was incomplete integration with honesty, not fake numbers.  
5. **Documentation co-evolution needs automation.** Trace Gate C and prompt metadata checks caught missing files faster than manual checklist reviews near the deadline.  
6. **PR-only main is a teaching tool as well as a safety tool.** The first rejected push taught the team more about branch protection than a slide deck would have.  
7. **Drafts then consolidate.** Per-member `docs/drafts/report-m*.md` files prevented edit wars on a single growing report until PM synthesis.

These lessons are the process optimization story required by D6: the team did not only build features; it repeatedly adjusted how humans supervise agents when evidence showed a risky shortcut.

---

## 14. Conclusion

MedLeaveAssist demonstrates a supervised agentic engineering process around a safety-relevant AI boundary: extract with an LLM, decide with deterministic code and humans, verify with offline tests and a blocking CI gate, and record what humans overruled. The team optimized parallel work through module ownership, frozen schemas, PR-only protected `main`, and co-evolving requirements/architecture/tests.

Process quality was evidenced by manageable requirement volatility (Fit Criteria refined without abandoning red lines), a visible shift in defect classes from architecture shortcuts to provider/integration plumbing, explicit ambiguity resolutions written into ADRs and AGENTS.md, and artifact co-evolution checked by CI where possible. Human oversight repeatedly caught agent proposals that would have weakened safety—schema edits, auto-approve paths, fabricated metrics, and incomplete assertions.

Remaining debts are explicit—provider token preflight completeness, some pending trace rows, durable access-log persistence, and operational polish—so readiness claims stay honest. The contribution table documents relative effort; the technical chapters document what each role built; the reflections document what each student learned about governing AI coding agents rather than merely prompting them.

---

