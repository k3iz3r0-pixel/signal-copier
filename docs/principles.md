# Principles

Retained from AGENTS.md (previous version) and applied to all phases:

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
