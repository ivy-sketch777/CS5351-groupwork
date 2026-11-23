\# Trace Matrix (追踪矩阵)



This matrix maps the requirements owned by Member 1 (Core \& State Machine) to their enforcing code components and verification tests.



|Req ID|Requirement Statement|Enforcing Component|Test / Evidence|Runtime Monitor|
|-|-|-|-|-|
|REQ-FR-001|Student can submit a medical leave request (Payload, dates, attachments).|`src/core/api.py` (`POST /api/apply`)|`test/offline/test\\\_api.py::test\\\_apply\\\_persists\\\_and\\\_returns\\\_draft`|API Gateway logs (200 OK rate).|
|REQ-FR-004|Student sees clear status, NEVER a fake success (draft/pending\_docs/in\_review/approved/rejected/failed).|`src/core/api.py` \& `CaseStatus` enum|`test\\\_api.py::test\\\_duplicate\\\_case\\\_id\\\_returns\\\_409`, `test\\\_status\\\_unknown\\\_case\\\_returns\\\_404`|DB state transition audit triggers.|
|REQ-FR-008|Route missing fields to manual review, allow supplements and counselor decisions.|`src/core/api.py` (`/api/review/...`, `/api/apply/.../supplement`)|`test\\\_api.py` (Strict state machine tests: only `in\\\_review` can be approved, 400 otherwise).|Review Queue backlog alerts.|
|REQ-ARCH-001|Authoritative write path: PolicyChecker -> ReviewQueue -> LeaveStore. LLM cannot write `approved`.|`src/core/database.py` \& `CaseDB`|Code Review + `test\\\_apply\\\_persists...` (asserts DB is updated by core, not AI). |Prometheus DB write metrics.|
|REQ-ARCH-003|Must use CityUHK SSO (Mocked in core phase).|`src/core/api.py` (`require\\\_counselor` dependency)|`test\\\_api.py::test\\\_review\\\_decision\\\_without\\\_token\\\_returns\\\_401`|Auth gateway 401 error rates.|
|REQ-ARCH-004|Sanitize and check access before running any AI model.|`src/core/api.py` (Execution order)|Integration test: Mock AI is never called if schema validation (422) fails.|API Request trace timings (Sanitize < AI call).|



