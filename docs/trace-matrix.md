# Trace Matrix（全局需求溯源）

本文件是唯一真源（根目录 `trace-matrix.md` 仅是指针）。覆盖需求文档 `requirement.docx` 中全部 FR / INV / ARCH / SEC / COST / PERF / QUAL / GOV 需求。

由 `test/offline/test_trace_matrix.py` 在 CI 中机械校验：ID 集合完整、无重复、代码引用非空、测试文件真实存在。

## 矩阵

| 需求 ID | 类型 | 代码位置 | 测试用例 | 状态 |
| --- | --- | --- | --- | --- |
| REQ-FR-001 | FR | `src/schemas.py` (`ApplicationPayload`), `src/core/api.py` (`/api/apply`) | `test/offline/test_api.py::test_apply_persists_and_returns_pending_docs`, `test/offline/test_schema_contract.py::test_application_payload_contract_fields_exact` | 已覆盖 |
| REQ-FR-002 | FR | `src/schemas.py` (`ExtractionResult`), `src/ai/`（成员 3 待交付） | `test/offline/test_schema_contract.py::test_extraction_result_contract_fields_exact`, `test/offline/governance/test_review_router.py::test_review_packet_shows_derived_exact_values` | 部分覆盖（AI 模块待交付） |
| REQ-FR-003 | FR | `src/core/mock_policy.py` (Mock), `src/policy/`（成员 2 待交付） | `test/offline/test_api.py::test_long_leave_flows_to_in_review`, `test/offline/test_schema_contract.py::test_policy_decision_contract_fields_exact` | 部分覆盖（动态规则待交付） |
| REQ-FR-004 | FR | `src/core/api.py`, `src/core/models.py`, `src/schemas.py` (`CaseStatus`) | `test/offline/test_integration_flow.py::test_full_review_chain_never_fakes_success`, `test/offline/test_api.py::test_status_unknown_case_returns_404` | 已覆盖 |
| REQ-FR-005 | FR | `src/governance/review_router.py`, `src/ai/`（成员 3 待交付） | `test/offline/test_integration_flow.py::test_supplement_reenters_review_queue`, `test/offline/governance/test_review_router.py::test_missing_docs_routes_to_review` | 部分覆盖（友好文案待交付） |
| REQ-FR-006 | FR | `src/ai/`（成员 3 待交付）, `src/governance/review_packet.py` | `test/offline/governance/test_review_router.py::test_review_packet_shows_derived_exact_values` | 待交付 |
| REQ-FR-007 | FR | `src/core/mock_policy.py`, `src/policy/`（成员 2 待交付） | `test/offline/test_api.py::test_long_leave_flows_to_in_review`, `test/offline/test_api.py::test_review_pending_returns_only_in_review` | 已覆盖（Mock 规则） |
| REQ-FR-008 | FR | `src/core/api.py`, `src/governance/review_router.py` | `test/offline/test_api.py::test_apply_missing_required_field_returns_422`, `test/offline/governance/test_review_router.py::test_router_never_recommends_approved` | 已覆盖 |
| REQ-INV-001 | INV | `src/core/api.py`, `src/core/mock_policy.py` | `test/offline/test_integration_flow.py::test_unauthenticated_decision_does_not_fake_success`, `test/offline/governance/test_review_router.py::test_router_never_recommends_approved` | 已覆盖 |
| REQ-INV-002 | INV | `src/schemas.py` (`PolicyDecision`), `prompts/prompt_v1.0.yaml` | `test/offline/test_schema_contract.py::test_policy_decision_result_enum_is_closed`, `test/offline/test_ci_governance.py::test_prompt_version_file_contains_required_metadata` | 已覆盖 |
| REQ-INV-003 | INV | `src/core/database.py`, `src/policy/`（成员 2 待交付） | `test/offline/test_schema_contract.py::test_policy_decision_contract_fields_exact` | 待交付（重叠检测） |
| REQ-INV-004 | INV | `src/schemas.py` (`ExtractedField`), `src/security/sanitize.py` | `test/offline/test_schema_contract.py::test_fabricated_sick_leave_json_is_rejected_by_contract`, `test/offline/security/test_sanitize.py::test_raw_injection_payload_does_not_survive_intact` | 部分覆盖 |
| REQ-INV-005 | INV | `src/core/mock_policy.py` | `test/offline/test_integration_flow.py::test_same_input_same_outcome_class` | 已覆盖（Mock 规则） |
| REQ-ARCH-001 | ARCH | `src/core/api.py`, `src/core/mock_policy.py` | `test/offline/test_integration_flow.py::test_unauthenticated_decision_does_not_fake_success`, `test/offline/test_ci_governance.py::test_extractor_policy_summarizer_module_boundaries` | 已覆盖 |
| REQ-ARCH-002 | ARCH | `src/ai/`, `src/policy/`（成员 2/3 待交付） | `test/offline/test_ci_governance.py::test_extractor_policy_summarizer_module_boundaries` | 已覆盖（边界门禁） |
| REQ-ARCH-003 | ARCH | `src/core/api.py` (`require_counselor`, CityUHK SSO 待集成) | `test/offline/test_api.py::test_review_pending_requires_auth` | 待交付（SSO） |
| REQ-ARCH-004 | ARCH | `src/security/sanitize.py`, `src/security/redact.py` | `test/offline/security/test_sanitize.py::test_injection_ignore_previous_instructions_is_filtered`, `test/offline/security/test_redact.py::test_redact_for_llm_never_includes_student_id` | 已覆盖 |
| REQ-SEC-001 | SEC | `src/security/sanitize.py` | `test/offline/security/test_sanitize.py::test_chinese_injection_is_filtered` | 已覆盖 |
| REQ-SEC-002 | SEC | `src/security/redact.py` | `test/offline/security/test_redact.py::test_redact_for_llm_never_includes_student_id` | 已覆盖 |
| REQ-SEC-003 | SEC | `src/security/access.py`, `src/governance/access_log.py` | `test/offline/security/test_access.py::test_authorized_access_is_logged_with_actor_and_time` | 已覆盖 |
| REQ-SEC-004 | SEC | `src/security/retention.py` | `test/offline/security/test_access.py::test_retention_on_day_30_purges` | 已覆盖 |
| REQ-COST-001 | COST | `src/ai/`（成员 3 待交付）, `prompts/prompt_v1.0.yaml` | `test/offline/test_ci_governance.py::test_prompt_version_file_contains_required_metadata` | 待交付（Token 计量） |
| REQ-PER-001 | PERF | `src/policy/`（成员 2 待交付） | `test/offline/test_ci_governance.py::test_extractor_policy_summarizer_module_boundaries` | 待交付（p95 基准） |
| REQ-QUAL-001 | QUAL | `src/schemas.py` (`PolicyDecision.rule_ids_fired`) | `test/offline/governance/test_review_router.py::test_policy_route_to_review`, `test/offline/test_integration_flow.py::test_same_input_same_outcome_class` | 已覆盖 |
| REQ-QUAL-002 | QUAL | `AGENTS.md` §6（冲突解决优先级）, `docs/ci-gate.md` | `test/offline/test_trace_matrix.py::test_agents_documents_conflict_priority` | 已覆盖 |
| REQ-GOV-001 | GOV | `src/governance/audit.py`, `src/schemas.py` (`AuditInfo`) | `test/offline/governance/test_audit.py::test_build_audit_requires_actor_and_rule_version`, `test/offline/test_schema_contract.py::test_audit_info_contract_fields_exact` | 已覆盖 |
| REQ-GOV-002 | GOV | `src/governance/review_router.py` | `test/offline/governance/test_review_router.py::test_low_confidence_routes_to_review` | 已覆盖 |
| REQ-GOV-003 | GOV | `src/governance/review_packet.py` | `test/offline/governance/test_review_router.py::test_review_packet_shows_derived_exact_values` | 已覆盖 |
| REQ-GOV-004 | GOV | `src/schemas.py` (`ExtractedField`), `src/governance/review_packet.py` | `test/offline/test_schema_contract.py::test_extracted_field_derived_value_is_visible`, `test/offline/governance/test_review_router.py::test_review_packet_shows_derived_exact_values` | 已覆盖 |
| REQ-GOV-005 | GOV | `.opencode/rules.md`, `prompts/prompt_v1.0.yaml`, `.github/workflows/ci.yml` | `test/offline/test_ci_governance.py::test_rules_file_exists_and_nonempty`, `test/offline/test_ci_governance.py::test_prompt_version_file_contains_required_metadata` | 已覆盖 |
| REQ-GOV-006 | GOV | `.github/workflows/ci.yml`, `docs/ci-gate.md` | `test/offline/test_ci_governance.py::test_ci_workflow_is_a_hard_gate`, `test/offline/test_schema_contract.py::test_fabricated_sick_leave_json_is_rejected_by_contract` | 已覆盖 |
| REQ-GOV-007 | GOV | `docs/trace-matrix.md`, `trace-matrix.md` | `test/offline/test_trace_matrix.py::test_trace_matrix_covers_all_requirements`, `test/offline/test_trace_matrix.py::test_trace_matrix_test_references_exist` | 已覆盖 |

## 状态说明

- **已覆盖**：确定性门禁已有测试与代码引用。
- **部分覆盖 / 待交付**：成员 1–4 的模块尚未合入；矩阵保留引用与门禁，模块交付后需由对应成员更新为「已覆盖」，并在 PR 中同步本文件。

## 覆盖口径

REQ-GOV-007 的 Fit Criterion 要求「100% FR 与 INV」；本矩阵同时覆盖全部 ARCH / SEC / COST / PERF / QUAL / GOV，共 32 个需求 ID，由 Gate C 强制校验。
