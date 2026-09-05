# Architecture

## Overview
Signal Copier is a high-performance, budget-conscious trading signal processing
and copying platform developed as a Python monorepo.

## Repository Structure
- `packages/signal_core/` — core signal library (canonical domain model:
  Signal, SignalIdentity, SignalEvent, SignalRevision, SignalInstruction,
  Price, PriceRange, ProviderSource, SourceIdentity, Instrument, enums,
  pure invariant functions, unified canonical-fingerprint).
- `packages/parser/` — Phase 2 parser engine: contract layer (`types.py`,
  `enums.py`), deterministic pipeline (`pipeline.py`), profile loader
  (`profiles.py`), regex safety (`safety.py`), OUTPUT ADAPTER
  (`output_adapter.py`; IR → Signal / SignalInstruction / non-signal).
- `packages/parser_profiles/` — declarative provider profiles
  (`data/common.py` + `provider_001`–`provider_017`).
- `src/signal_copier/` — application entry point (stub).
- `docs/` — architecture, principles, phase-status, design, ADRs, corpus,
  agent instructions.
- `tests/unit/`, `tests/integration/` — Phase 1 adversarial and unit tests.
- `tests/parser/` — Phase 2 parser tests (contract, lexical, semantic,
  adversarial, blocks, providers/provider_001–017).
- `tests/fixtures/providers/` — per-provider fixture data (001–012
  synthetic; 013–017 verbatim real-corpus excerpts).
- `benchmarks/` — Step 9 / Step 10 controlled performance optimization
  artifacts (preserved immutable).
- `apps/`, `infrastructure/` — reserved for future phases.
- `scripts/` — verification and setup helpers.

## Phase Boundaries
- Phase 1 (Signal Core): COMPLETE. See `docs/phase-status.md` and
  `docs/phase-1-signal-core-design.md` for the authoritative state. NO
  parser, NO provider adapters, NO Telegram/Discord, NO broker adapters,
  NO execution, NO strategy, NO risk, NO database, NO Redis, NO analytics,
  NO replay, NO backtesting, NO AI.
- Phase 1.1 (Architecture Freeze / Remediation): COMPLETE. Audit,
  documentation consistency, canonical-fingerprint contract unification,
  canonical-snapshot contract documentation. No code in
  `packages/signal_core/` was modified beyond the contract unification
  fixes; all 334 tests pass.
- Phase 2 (Parser Engine): IMPLEMENTATION COMPLETE (adopted scope;
  reconciled 2026-09-05). Design document
  `docs/phase-2-parser-engine-design.md`; ADRs `docs/adr/0001`–`0013`;
  contract layer + engine + 17 provider profiles + real-corpus batch 1
  (providers 013–017) + safety hardening + multi-block (ADR 0013) + OUTPUT
  ADAPTER (`packages/parser/output_adapter.py`, design §25 step 5).
  Adopted by explicit owner decision on 2026-09-05. NO Telegram/Discord,
  NO broker adapters, NO execution, NO strategy, NO risk, NO database,
  NO Redis, NO analytics, NO replay, NO backtesting, NO AI, NO correlation
  (all Phase 3+; none approved). Deferred: corpus batch-2 (M14/M15/M18/
  M29/M28); MULTI_SIGNAL capability enforcement (declarative only per
  ADR 0013). Not production-ready.
- Phase 3: NOT STARTED, NOT APPROVED.

Future phases (not implemented):
- Signal sources (e.g., Telegram/Discord adapters — must stay out of core).
- Correlation layer (consumes ParseResult + CorrelationRequest).
- Broker/execution adapters (must stay out of core).
- Risk management, replay, analytics, persistent audit/state storage.
- Strategy engine (user-specific strategies, risk parameters).

## Key Assumptions (explained, not hidden)
- Core logic stays in `packages/signal_core`; application wiring in `src/`.
- Adapter pattern separates provider-specific and broker-specific logic
  from core.
- Simple architecture preferred over distributed systems.
- Minimal dependencies; budget-conscious development via `.venv` + `uv`.
