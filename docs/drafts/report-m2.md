# D6 Report Section — Rule Engine & Decision Design (Member 2)

## Rule Engine & Decision Design

Leave decisions in MedLeaveAssist are made entirely by a deterministic rule
engine; AI never participates in any approval decision. The engine exposes
`evaluate_policy(payload) -> PolicyDecision` as its contract and loads rules
dynamically from `policy_v1.0.yaml`, achieving "change rules without changing
code" (REQ-FR-003).

The design has four layers:
1. **Data model** — `Rule` / `RuleSet` dataclasses whose fields align with
   `PolicyDecision`; `action` strictly uses the `PolicyResult` enum, forbidding
   magic strings.
2. **Safe condition evaluator** — an `ast` whitelist walker (no
   `eval/exec/compile`) that only allows boolean/comparison/name/constant
   nodes; any call, attribute access, subscript, or power operation is
   rejected; length and node-count limits guard against DoS (REQ-SEC-001).
3. **Strict loader** — validates every field; missing fields, invalid actions,
   typos, and `bool` masquerading as `int` all fail closed; the rule set is
   cached by resolved absolute path.
4. **Decision engine** — iterates in descending priority (larger number first),
   short-circuits immediately on a `fail-closed` hit; otherwise aggregates with
   `route-to-review` winning over `pass`.

Key safety properties:
- All exceptions are caught and converted to `fail-closed`; the engine never
  raises and never returns a fake success (REQ-INV-001); no rule matched means
  default-deny.
- The same input produces identical results across 100 runs (REQ-INV-005); no
  `datetime.now()` is used.
- A single decision takes ~0.04 ms, far below p95 < 500 ms (REQ-PER-001).
- For the REQ-FR-007 "consecutive teaching days" semantics, `duration_days`
  counts only Monday–Friday, preventing a Friday→Monday range from being
  miscounted as 4 calendar days.

The implementation is backed by 63 offline tests covering the normal paths,
boundaries (weekends, invalid dates), and injection-attack negatives
(`__import__`, attribute access, power bombs, unknown variables, type
mismatches).

## Reflection (Member 2 — Rule Engine, ~350 words)

Building the rule engine taught me that "deterministic" is a design discipline,
not a single function call. My biggest early mistake was a semantic one: I
wrote "smaller priority number = higher priority" while the assigned values
(1000 for overlap) clearly meant the opposite. Catching that contradiction
before writing code prevented the short-leave rule from silently shadowing
critical blocks — a reminder that requirements and their numbers must be
reconciled, not just copied.

The second lesson was about security by construction. Instead of trusting YAML
expressions, I built an AST whitelist evaluator that forbids calls, attribute
access, and even exponentiation, so a malicious condition cannot execute code.
A later self-audit found that `None < int` raised a raw `TypeError` that would
have bypassed fail-closed handling; wrapping comparisons turned a subtle leak
into a clean `PolicyConfigError`. This reinforced that "fail-closed" must be
verified at every boundary, not assumed.

Configuration over hardcoding was the core architectural win. Every threshold
and action lives in YAML, and the loader strictly rejects typos, invalid
actions, and missing fields, letting non-developers adjust policy without
risking code changes.

Finally, the requirements audit was humbling: my initial `duration_days`
counted calendar days, which violated the "consecutive teaching days"
requirement. I fixed it to exclude weekends and realigned all tests. I also
learned to draw clear module boundaries — overlap detection and
explanation-with-rule-ID depend on the API/DB layers, so I documented these as
handover tasks rather than overreaching into others' modules. The plan →
approve → code workflow enforced by our AGENTS.md kept changes reviewable and
prevented scope creep.
