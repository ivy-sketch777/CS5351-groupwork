\# Invariant Register (不变量登记表)

This document lists the non-negotiable constraints of the MedLeaveAssist system. Any violation of these invariants is considered a critical system failure.

|Invariant ID|Statement (Constraint)|Source Req|Enforcing Component|Verification Method|Operational Fallback (If Violated)|
|-|-|-|-|-|-|
|INV-001|No request shall be APPROVED without passing all mandatory deterministic rules (date limits, document completeness).|REQ-INV-001|`PolicyChecker` \& `CaseStateMachine` |`test/offline/test\\\_api.py` (Negative tests attempting to approve without policy pass return 400/422).|Set case status to `failed` and immediately trigger a P1 alert to the admin console. Log the attempted bypass.|
|INV-002|The AI's output (LLM summary/extraction) is NOT the authority for eligibility or final decision.|REQ-INV-002|`CaseService` \& `ReviewUI` |Integration tests ensuring `ExtractionResult` does not trigger state changes directly.|Ignore AI output, route case directly to `in\\\_review` (Human Review Queue) with a "low confidence" flag.|
|INV-003|Overlapping approved leave for the same student is strictly forbidden (0 double-booked days).|REQ-INV-003|`PolicyChecker` \& `Database Constraints` |`test/offline/test\\\_api.py` (Concurrent submission tests assert 0 duplicates).|Reject the new application with `409 Conflict` and instruct the student to contact the Registrar.|
|INV-004|AI must not invent medical facts (dates, rest days) not present in the source.|REQ-INV-004|`AISanitizer` \& `ExtractionSchema`|Adversarial LLM tests verifying empty fields are returned as `None` rather than hallucinated data.|Discard the AI extraction result, set status to `pending\\\_docs`, and ask the student to manually re-enter the dates.|
|INV-005|Consequential decisions must record the exact rule, model, and prompt versions.|REQ-GOV-001|`AuditLogger` \& `CaseDB` |Database checks ensuring `rule\\\_version`, `model\\\_version`, and `prompt\\\_version` are 100% populated.|Block the decision from being saved, return `500 Internal Server Error`, and alert the IT security team.|





