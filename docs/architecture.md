# Architecture

## Overview
Signal Copier is a high-performance, budget-conscious trading signal processing
and copying platform developed as a Python monorepo.

## Repository Structure
- `packages/signal_core/` — core signal library (interfaces, determinism, audit).
- `src/signal_copier/` — CLI / application entry point.
- `docs/` — architecture, principles, ADRs, agent instructions.
- `tests/unit/`, `tests/integration/` — test scaffolding (Phase 0: empty).
- `scripts/` — verification and setup helpers.
- `apps/`, `benchmarks/`, `infrastructure/` — reserved for future phases.

## Phase Boundaries
Phase 0: repository foundation, documentation, persistent agent instructions,
CI skeleton, tooling verification. NO trading code, NO parser, NO Telegram,
NO broker, NO database, NO analytics, NO replay/backtesting.

Future phases (not implemented in Phase 0):
- Signal parsing (provider-independent core + provider-specific adapters).
- Signal sources (e.g., Telegram adapter — must stay out of core).
- Broker/execution adapters (must stay out of core).
- Risk management, replay, analytics, persistent audit/state storage.

## Key Assumptions (explained, not hidden)
- Core logic stays in `packages/signal_core`; application wiring in `src/`.
- Adapter pattern separates provider-specific and broker-specific logic from core.
- Simple architecture preferred over distributed systems.
- Minimal dependencies; budget-conscious development via `.venv` + `uv`.
