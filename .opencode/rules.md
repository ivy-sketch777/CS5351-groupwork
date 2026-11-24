# OpenCode Project Rules (MedLeaveAssist)

1. **Data Contract & Red Lines**:
   - Treat `src/schemas.py` and `AGENTS.md` as high-priority contracts. Do not alter schema contracts unless explicitly approved and aligned across modules.
   - AI components only extract/summarize/assist; deterministic code owns policy decisions, state transitions, access control, and fail-closed behavior. Never fabricate `approved` status.

2. **Module Boundaries & Human Supervision**:
   - Respect module ownership (`src/core/`, `src/policy/`, `src/ai/`, `src/security/`, `src/governance/`, `test/`, `.github/workflows/`).
   - When cross-module changes or safety-critical edits are needed, state the plan, affected files, and test impact clearly before editing.
   - Do not modify unrelated files or delete existing tests/mocks that are still imported unless updating their callers in the same task.