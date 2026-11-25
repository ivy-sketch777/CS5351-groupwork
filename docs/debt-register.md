# Debt Register

- **Status:** Living register, reviewed 2026-11-25
- **Owner:** Member 5 (QA, CI & PM), Tang Man Kit (55641875)
- **Consolidation owner:** Member 1
- **Priority order (REQ-QUAL-002):** reliability -> input-boundary safety -> accountability -> cost

This register tracks known technical and governance debt that is deliberately not fixed inside Member 5's path scope. An item is closed only when its exit criterion is demonstrated by a test or an admin configuration record.

| ID | Debt | Source / evidence | Severity | Owner | Status | Mitigation | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QA-DEBT-001 | Branch protection not enabled; `blocking-gate` is not yet a required check on `main` | `docs/ci-gate.md` section 2 | High | M1 + repository admin | Open | Follow Settings steps or `gh api` command in `docs/ci-gate.md` | Red PR is unmergeable; strict mode and no-bypass are enabled |
| QA-DEBT-002 | API still imports `src/core/mock_policy.evaluate_policy` instead of the delivered real policy engine | `src/core/api.py`; M2 handover notes | High | M1 | Open | Replace import with `from src.policy import evaluate_policy`; signature is backward compatible | Full offline suite green with real rules; student-facing messages include fired Rule IDs |
| QA-DEBT-003 | AI extraction and summarizer modules are absent | `src/ai/` missing; trace matrix rows marked Pending | High | M3 | Open | Deliver modules with derived-field visibility and token control | AI tests pass and related trace matrix rows are Covered |
| QA-DEBT-004 | Prompt metadata uses placeholder `model_version: pending-ai-owner` | `prompts/prompt_v1.0.yaml` | Medium | M3 | Open | Set the real model version; append changelog on every prompt change | `test_prompt_version_file_contains_required_metadata` passes with a real version string |
| QA-DEBT-005 | Regex injection denylist is not complete; novel phrasings may pass | ADR-001, Consequences | Medium | M4 | Open | Monitor review packets for false positives; extend denylist with reviewed cases | Adversarial suite covers the new case or acceptance is explicitly documented |
| QA-DEBT-006 | Sanitize -> redact -> AI call order is not wired in the API | ADR-001; REQ-ARCH-004 | High | M1 | Open | Call sanitize and redact before setting `ai_allowed` | Integration test proves zero model calls when validation or auth fails |
| QA-DEBT-007 | Several trace matrix rows remain Pending or Partially Covered | `docs/trace-matrix.md` | Medium | M1 (consolidation) + module owners | Open | Update each row in the same PR that delivers its module | Gate C passes with all rows Covered |
| QA-DEBT-008 | CityUHK SSO is not integrated; only a mock counselor token exists | `src/core/api.py` | Medium | M1 | Open | Replace mock token check with SSO verification | Auth tests assert SSO-only path and no local credential store |
| QA-DEBT-009 | p95 benchmark for policy check (excluding LLM) is missing | REQ-PER-001 | Low | M2 | Open | Add an offline timing benchmark | Report shows p95 < 500 ms |
| QA-DEBT-010 | Token metering and hard cap 3000 are not implemented | REQ-COST-001 | Medium | M3 | Open | Enforce a counter before model calls; route simple cases to rules | Test shows zero model calls above the cap |
| QA-DEBT-011 | Overlap detection needs historical DB state from Core/Security | M2 handover: engine does not query DB | High | M1 + M4 | Open | Query LeaveStore and pass `overlap_flag=True` | REQ-INV-003 fail-closed test with a real overlapping approved leave |
| QA-DEBT-012 | Gate and trace matrix ownership moved to M1; M5 cannot self-repair them | 2026-11-25 team notice | Low | M1 | Open | Route all gate changes through M1 review | PRs touching `ci.yml` or `docs/trace-matrix.md` are reviewed by M1 |
| QA-DEBT-013 | `git status` shows line-ending-only modifications on untouched files | `core.autocrlf=true` with LF working tree | Low | M1 (repo hygiene) | Documented | Use `git diff --numstat` for content review; avoid mass line-ending rewrites | Repository uses a consistent `.gitattributes` policy |

Debt that is resolved is moved to `docs/bug-diary.md` with its verification evidence rather than deleted from the history.
