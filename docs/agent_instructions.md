# Persistent Agent Instructions — Signal Copier

## Phase
The current phase is determined from the project's approved phase
status and documentation (see docs/architecture.md, AGENTS.md, and
relevant phase markers). Consult the current phase before implementing.

Do not implement future phases without explicit approval.

## Core Principles (retained from previous AGENTS.md)
1. Correctness before optimization.
2. Measure before optimizing.
3. Deterministic behavior in the live trading path.
4. No AI inference in the live signal execution path.
5. No broker-specific logic in the signal core.
6. No Telegram-specific logic in the signal core.
7. Avoid unnecessary I/O in the hot path.
8. Financial operations must be idempotent.
9. Important state changes must be auditable.
10. Never silently discard malformed or ambiguous signals.
11. Never silently modify provider data.
12. Every production bug must receive a regression test.
13. Do not introduce dependencies without justification.
14. Do not introduce infrastructure before it is needed.
15. Prefer simple architecture over premature distributed systems.

## Role Definitions
- ARCHITECT: owns docs/architecture.md, docs/principles.md, ADRs, interfaces,
  phase approvals. Must approve structural changes before Builder acts.
- BUILDER: implements against Architect-approved specs. Must include regression
  tests for any production bug. Must run ruff, mypy, pytest before reporting done.
- REVIEWER: independent review of Builder output. Checks: no future-phase
  leakage, tests preserved/added, ruff/mypy clean, diff inspected, no silent
  modifications to provider data or ambiguous signals.
- TESTING: owns test scaffolding, deterministic/idempotency verification,
  regression-test enforcement. Creates appropriate test coverage for the
  current phase; ensures no silent modifications and deterministic behavior.

## Development Rules (before/during/after)
Before architecture changes: read docs/architecture.md, docs/principles.md,
relevant ADRs.
Before implementing: understand existing interfaces, write/update tests,
preserve existing behavior, keep changes focused.
After implementation: run tests, run ruff, run mypy, inspect final diff,
report architectural/performance implications.

Never implement future phases without explicit instruction.
