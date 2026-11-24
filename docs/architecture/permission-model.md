# Permission Model (权限模型)

Owner: Member 4 (Security & Governance)  
Default: **no read, no write** unless a path is explicitly whitelisted below.  
Related: `AGENTS.md` module boundaries, `src/security/access.py`, REQ-SEC-003.

This document covers two layers required by the course and by MedLeaveAssist:

1. **Coding-agent file permissions** — what each role’s AI coding agent may read/write in the repo (D2 Permission Model).
2. **Runtime application permissions** — who may view raw medical content at runtime (REQ-SEC-003).

---

## 1. Coding-agent roles

| Agent role | Human owner | Purpose |
|------------|-------------|---------|
| `core-agent` | Member 1 | Core API, state machine, persistence |
| `policy-agent` | Member 2 | Deterministic rule engine |
| `ai-agent` | Member 3 | LLM extraction / prompts |
| `secgov-agent` | Member 4 | Sanitize, redact, access, audit, review routing |
| `qa-agent` | Member 5 | Tests, CI, verification governance |
| `plan-agent` | Any (read-mostly) | Planning / architecture review before code |

Symbols: `R` = read, `W` = write, `-` = denied.

### 1.1 Path whitelist matrix

| Path | core | policy | ai | secgov | qa | plan |
|------|:----:|:------:|:--:|:------:|:--:|:----:|
| `src/schemas.py` | R | R | R | R | R | R |
| `src/core/` | R/W | - | - | - | R | R |
| `src/policy/` | R | R/W | - | - | R | R |
| `src/ai/` | R | - | R/W | - | R | R |
| `src/security/` | R | - | R | R/W | R | R |
| `src/governance/` | R | - | - | R/W | R | R |
| `test/offline/test_api.py` (and other core API tests) | R/W | - | - | - | R/W | R |
| `test/offline/policy/` | - | R/W | - | - | R/W | R |
| `test/offline/ai/` | - | - | R/W | - | R/W | R |
| `test/offline/security/` | - | - | - | R/W | R/W | R |
| `test/offline/governance/` | - | - | - | R/W | R/W | R |
| `test/live/` | - | - | R/W | - | R/W | R |
| `prompts/` | R | R | R/W | R | R | R |
| `docs/architecture/invariants.md` | R/W* | R | R | R | R | R |
| `docs/architecture/trace-matrix.md` | R/W* | R | R | R | R | R |
| `docs/architecture/permission-model.md` | R | R | R | R/W | R | R |
| `docs/architecture/adr/` | R | R | R | R/W | R | R |
| `docs/architecture/runtime-policy-catalog.md` | R | R/W | R | R | R | R |
| `docs/architecture/memory-design.md` | R | R | R/W | R | R | R |
| `docs/req/` | R | R/W† | R | R | R/W | R |
| `AGENTS.md` / `.opencode/` / `.agent/` | R | R | R | R | R/W‡ | R |
| `.github/` | - | - | - | - | R/W | R |
| `transcripts/` / `transcript/` | R/W (own) | R/W (own) | R/W (own) | R/W (own) | R/W (own) | R |
| Secrets / `.env` / credential files | - | - | - | - | - | - |

\* Member 1 owns invariants + FR-focused trace matrix rows.  
† Member 2 assists Fit Criteria for REQ-FR-003 / REQ-INV-001.  
‡ Member 5 final-reviews coding governance files.

### 1.2 Hard denials (all roles)

- **No write** to `src/schemas.py` without a human-approved ADR and team consensus.
- **No write** outside the agent’s owned module directories.
- **No read/write** of production secrets, API keys, or real student medical dumps in the repo.
- **No** inventing cross-module internal calls that bypass public package exports (`src.security`, `src.governance`).

### 1.3 Integration rule

Wiring `sanitize` / `redact` / `route_decision` / `build_audit` into `src/core/api.py` is a **Member 1** change.  
`secgov-agent` may propose call-order contracts in docs/tests, but must not edit `src/core/` unless the human owner explicitly expands the whitelist for that task.

---

## 2. Runtime application permissions (REQ-SEC-003)

Enforcing code: `src/security/access.py`, access audit: `src/governance/access_log.py`.

| Role | View own case raw medical | View others’ raw medical | Approve / reject leave | Notes |
|------|:--------------------------:|:------------------------:|:----------------------:|-------|
| `student` | Yes (owner match) | No | No | Identity = case owner `student_id` |
| `advisor` | Yes | Yes | Yes (via Core review APIs) | Sensitive open must be logged |
| `admin` | Yes | Yes | Yes | Same logging expectation |
| unknown / other | No | No | No | `AccessDenied` |

### 2.1 Access-log requirement

Any authorized open of raw medical content must record at least:

- `case_id`
- `actor_id`
- `role`
- `action` (default `view_raw_medical`)
- UTC ISO-8601 `timestamp`

Offline helper: `log_sensitive_access(...)`. Persistence to DB is owned by Core when integrating.

### 2.2 Retention (REQ-SEC-004)

Sensitive working copies of **closed** cases should be purged when  
`now >= closed_at + retention_days` (default **30** days).  
Decision helper: `src/security/retention.should_purge`. Actual purge job remains a Core/ops concern.

---

## 3. Authority boundaries (advisory vs authoritative)

| Component | Authority |
|-----------|-----------|
| LLM / `ExtractionResult` | **Advisory only** — never writes `approved` |
| Policy engine (`PolicyDecision`) | **Authoritative** for fail-closed / route-to-review / pass signals |
| Governance review router | **Advisory recommendation** only; may recommend `in_review`, **never** `approved` |
| Human counselor (Core review path) | **Authoritative** for approve / reject after review |
| Security sanitize / redact | **Mandatory pre-AI gate** before model input |

---

## 4. Verification

| Check | Evidence |
|-------|----------|
| Student cannot view another student’s raw content | `test/offline/security/test_access.py` |
| Advisor access can be logged | `test_access.py::test_authorized_access_is_logged_with_actor_and_time` |
| Retention boundary at day 30 | `test_access.py` retention cases |
| Agent must not modify foreign modules | Human review + `AGENTS.md`; CI structural gates (Member 5) |

---

## 5. Change policy

Changing any whitelist row, runtime role rule, or retention default requires:

1. Update this file in the same PR.
2. If the change affects a safety boundary, add or amend an ADR under `docs/architecture/adr/`.
3. Human approval before merge (safety-critical path).
