# AI Memory, State, and Token-Budget Design

**Owner:** Member 3 (AI Component)
**Status:** Implementation-aligned design draft
**Requirements:** REQ-FR-002, REQ-FR-005, REQ-FR-006, REQ-INV-002, REQ-INV-004, REQ-COST-001

## 1. Scope and authority boundary

The AI component extracts medical facts and returns an advisory `ExtractionResult` using the shared Pydantic contract. Its four fields are hospital name, visit date, recommended rest duration, and diagnosis. Extracted fields are marked `derived=True` and carry confidence. The AI component does not determine leave eligibility, decide whether materials are complete, approve or reject an application, or write case status. The policy, core, and human-review components retain those authorities.

The component also supplies deterministic, template-based student guidance and counsellor summaries. They use caller-provided `PolicyDecision` facts and application metadata; these functions do not make additional model calls. In particular, the summarizer does not infer document completeness or recommend approval.

## 2. Memory and state inventory

| State | Lifetime and owner | Persistence and boundary |
|---|---|---|
| Source attachment | Upload/storage component | The AI component does not fetch, retain, or delete the source file. Access control and retention belong to the owning security/storage components. |
| Sanitized and redacted document text | Supplied to one extraction call; available in process while handled | The AI module has no explicit file/database persistence for it. This does not imply secure memory erasure or provider-side non-retention. |
| Prompt instructions | Loaded from `prompts/prompt_v1.0.yaml` when the extractor module is imported | Version-controlled. A running process may need a restart/reload to pick up a changed prompt. |
| Request JSON schema | Constructed from the shared `ExtractionResult` and `ExtractedField` contract for each request | Request-local; it is not an independent application data contract. |
| Provider response | Returned for an individual request | Parsed and locally checked before the extraction function returns an advisory result. Provider handling and retention depend on the configured service. |
| `ExtractionResult` | Returned to the caller | The core/storage owner decides whether and how to persist it, associate it with source evidence, and authorize access. |
| CityU `last_usage` | Mutable metadata on a `CityUProvider` instance, populated by `generate()` | Per-instance operational metadata, not a durable audit record. The adapter resets it at the start of `generate()`; a blocked preflight does not call `generate()`. Callers must not mistake previous instance state for usage from a blocked attempt. |
| Prompt and model versions | Prompt module and provider configuration | Must be attached to a durable audit record by the owning core/governance integration if required. The result schema itself does not carry these metadata. |
| Approval, rejection, review, and case state | Core, policy, and governance components | Not owned, persisted, or changed by the AI component. |

## 3. Request context, retrieval, and resumability

An extraction request is single-turn. It uses the current extraction instructions, the current preprocessed certificate text, and the response contract. The CityU adapter adds explicit JSON-shape instructions to the system message. The component does not retrieve prior applications, conversation history, or stored medical evidence, and does not retain cross-session conversational memory.

There is no AI checkpoint or resumable extraction state. If a request is interrupted, any retry is a new caller-controlled attempt and must repeat applicable authorization, sanitization, and budget checks. Provider adapters disable automatic SDK retries. An ambiguous timeout must not be treated as zero usage or as proof that the provider did not process the request.

The AI component has no prompt-history compaction. Safety and extraction instructions are assembled anew for each request. It does not silently truncate source text to make an oversized request fit, because that could remove decision-relevant evidence.

## 4. Input, privacy, and access preconditions

The `ai_allowed` argument is a caller-supplied precondition, not an authentication or authorization mechanism. The integration must authenticate and authorize the actor, sanitize untrusted text, and redact irrelevant personal data before it sets `ai_allowed=True` or sends text to a provider. The AI component cannot independently verify that those upstream checks occurred.

The extraction provider receives the document argument and extraction instructions. Application identifiers and unrelated personal data must not be included in that text. The summary function can receive a student display name and document status from its caller, but it formats these values locally and does not send them to an LLM. Authorized access, UI rendering, data retention, and deletion remain responsibilities of their owning modules. This component makes no claim of secure erasure, complete audit persistence, or provider-side data deletion.

## 5. Token-budget policy

REQ-COST-001 requires average usage of at most 1,500 tokens per request, a hard cap of 3,000 tokens per request, and zero model calls for eligible simple requests. The application request budget is interpreted as input plus output token usage; it is separate from tokens used by a coding agent during development.

The extractor reserves `MAX_OUTPUT_TOKENS = 300` and allows generation only when the provider returns a usable input count satisfying:

```text
input_tokens + 300 <= 3000
```

It skips provider I/O when `ai_allowed` is not exactly `True`, when the caller marks a simple request, or when the document is empty. This flag does not itself prove authorization. The caller—not the AI module—determines whether a request is a simple case that can use deterministic processing.

For a supported provider, preflight must count the exact model request, including instructions, supplied document, and any schema or message framing included by that provider. A failed, invalid, or over-budget count fails closed and must not invoke generation. The extractor also checks provider-reported total usage after generation; this detects inconsistent or excessive reported usage but cannot prevent tokens already consumed. A post-call check is not a substitute for the pre-generation cap.

## 6. Provider-specific status and evidence

The retained `OpenAIProvider` implements a pre-count followed by a structured-output Responses request. Its compatibility with the CityU deployment has not been established.

`CityUProvider` uses Chat Completions. Its configured gateway rejected `response_format=json_schema` with HTTP 400. Two attempted token-count routes returned HTTP 405. These observations establish that the tested routes/settings were rejected; they do not prove every possible gateway token-count configuration is unavailable. No model-matched tokenizer plus complete CityU Chat Completions framing has been verified for this alias.

Accordingly, `CityUProvider.count_input_tokens()` raises `TokenBudgetUnavailable`. Through the ordinary `extract()` path, this causes an empty, fail-closed `ExtractionResult` and no generation call. CityU production extraction is therefore an incomplete integration, and REQ-COST-001 is not satisfied by that path. Do not bypass the preflight in a production call, treat a byte estimate or mock count as a real token count, or describe the CityU adapter as a working production extraction path.

The historical five-case evaluation used an experimental adapter and generated directly rather than through the protected production preflight. It is evidence about those experimental calls only, not evidence that the production hard cap works.

## 7. Experimental usage evidence

The following values were reported for five earlier synthetic CityU cases. They are historical provider-reported usage, not measurements made by this document or by the production preflight.

| Synthetic case | Input tokens | Completion tokens | Total tokens |
|---|---:|---:|---:|
| `migraine_full` | 260 | 77 | 337 |
| `gastro_other_hospital` | 263 | 88 | 351 |
| `fever_south_clinic` | 261 | 87 | 348 |
| `missing_diagnosis` | 255 | 85 | 340 |
| `issue_date_not_visit` | 273 | 87 | 360 |
| **Mean over five cases** | **262.4** | **84.8** | **347.2** |

All five synthetic cases were reported as passing their expected-value checks; the missing-diagnosis case returned no diagnosis, and the issue-date case distinguished issue date from visit date. The observed maximum total was 360 tokens. This small, short-text sample does not establish a population-wide average, guarantee that any future request is below 3,000 tokens, or verify production integration. The experiment used a 300-token output setting, which is an output limit, not a proven total-request limit.

## 8. Verification, monitoring, and open dependencies

The current checkout was rechecked during this document review: all 37 Member 3 AI offline tests passed. These deterministic tests use mocks to exercise contract validation, evidence grounding, simple-request bypass, preflight failure and budget boundaries, timeouts, provider usage handling, and CityU adapter fail-closed behavior. Mock counts verify program branches, not real gateway tokenizer behavior.

The live-test package was rechecked and one test collected successfully; collection is not a live API run. The five-case file `evaluate_cityu_five.py` must be explicitly selected because its name does not match default pytest discovery. The historical five-case results above came from the experimental path. Do not combine these evidence types or claim that the five cases exercised production CityU preflight.

The reviewed five-case evaluator has outstanding reliability gaps: it computes and prints each case's `passed` flag but only asserts generation success at the end; its helper omits production low-confidence filtering; experimental usage metadata can survive a failed attempt; and provider failures do not stop subsequent cases. Consequently a pytest pass alone is insufficient evidence of correct extraction, and failed-attempt usage must not be trusted without checking the individual record. These are evaluation-code limitations, separate from the protected production extractor, and were not changed as part of this documentation task.

Before enabling production CityU generation, the team needs a verified pre-generation count for this exact deployment and full request framing, or an explicitly accepted alternative requirement. The verification should establish that the count covers the exact model alias, all messages and relevant formatting, and the output/reasoning-token semantics. Offline tests should verify zero generation calls on preflight errors and over-budget inputs, including boundary cases. Live quality/usage evaluation should remain opt-in, use synthetic documents, and record actual provider-reported usage separately from estimates.

The full offline suite was attempted during this document review and stopped at collection because the active Python environment lacked FastAPI. FastAPI is declared in the current `requirements.txt`, which has no merge-conflict markers. Conflict markers had been reported in a different earlier snapshot, so that historical repository issue must not be confused with the current missing-installation problem. No full-suite pass is claimed.
