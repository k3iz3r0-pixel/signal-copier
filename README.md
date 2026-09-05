# Signal Copier

Phase 1 — Signal Core (COMPLETE). Phase 1.1 — Remediation (COMPLETE).
Phase 2 — Parser Engine (IMPLEMENTATION COMPLETE, adopted scope;
reconciled 2026-09-05). Phase 3 NOT STARTED, NOT APPROVED.

See `docs/phase-status.md` for the authoritative phase status.

## Status
- Signal Core complete: canonical domain model in `packages/signal_core/`
  (Signal, SignalIdentity, SignalEvent, SignalRevision, SignalInstruction,
  Price, PriceRange, ProviderSource, SourceIdentity, Instrument, enums).
- Parser Engine complete (adopted scope): contract layer + deterministic
  pipeline in `packages/parser/`, 17 provider profiles in
  `packages/parser_profiles/` (013–017 verbatim real-corpus), regex safety,
  multi-block signals (ADR 0013), and the OUTPUT ADAPTER
  (`packages/parser/output_adapter.py`: ParseResult → Signal /
  SignalInstruction / explicit non-signal).
- Deferred by owner instruction: corpus batch-2 (M14/M15/M18/M29/M28);
  MULTI_SIGNAL capability enforcement (declarative only per ADR 0013).
- Phase 3 (correlation, Telegram/Discord ingestion, broker adapters,
  execution, strategy, risk, database, Redis, replay, backtesting,
  analytics, AI) is NOT STARTED and is NOT APPROVED.
- Architecture and principles documented in `docs/`.
- Phase-status and design documents in `docs/phase-status.md` and
  `docs/phase-1-signal-core-design.md`.

## What Exists
- `packages/signal_core/` — canonical domain model (enums, value objects,
  domain objects, pure invariant functions, unified canonical-fingerprint).
- `packages/parser/` — parser contract layer, deterministic pipeline,
  profile loader, regex safety, OUTPUT ADAPTER.
- `packages/parser_profiles/` — declarative provider profiles
  (provider_001–provider_017).
- `src/signal_copier/` — application entry point stub.
- `docs/architecture.md`, `docs/principles.md`, `docs/agent_instructions.md`,
  `docs/phase-status.md`, `docs/phase-1-signal-core-design.md`,
  `docs/phase-2-parser-engine-design.md`, `docs/adr/0001`–`0013`,
  `docs/corpus/`, `docs/invariant_matrix.md`.
- `tests/unit/`, `tests/integration/` — Phase 1 adversarial and unit tests.
- `tests/parser/` — parser contract/lexical/semantic/adversarial/blocks and
  per-provider tests; `tests/fixtures/providers/` — fixture data.
- `benchmarks/` — Step 9 / Step 10 controlled performance optimization
  artifacts (preserved immutable).
- `.github/workflows/ci.yml` — Ruff + mypy + pytest.

## Tooling
Python 3.13, uv, ruff, mypy, pytest.
See `pyproject.toml`.

## Exclusions (intentional; not implemented in Phase 2)
Telegram/Discord adapters, broker adapter, execution engine, strategy
engine, risk engine, database, Redis, analytics, replay, backtesting,
trading logic, correlation, production deployment infrastructure. These
belong to Phase 3+ and may NOT be implemented without explicit approval.
