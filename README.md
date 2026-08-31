# Signal Copier

Phase 0 — Repository and engineering foundation.

## Status
- Foundation only; no trading functionality implemented.
- No signal parser, no Telegram integration, no broker integration, no database.
- Architecture and principles documented in `docs/`.
- Persistent agent instructions: `.agent_instructions.md`.

## What Exists
- `packages/signal_core/` (reserved for core library — empty in Phase 0)
- `src/signal_copier/` (stub CLI entry)
- `docs/architecture.md`, `docs/principles.md`, `docs/agent_instructions.md`
- `.agent_instructions.md` (persistent instructions)
- `tests/unit/`, `tests/integration/` (scaffold only)
- `.github/workflows/ci.yml` (skeleton)
- `scripts/setup_verify.sh`

## Tooling
Python 3.13, uv, ruff, mypy, pytest, pre-commit, hypothesis.
See `pyproject.toml`.

## Exclusions (intentional)
Signal parser, Telegram adapter, broker adapter, database, analytics,
replay/backtesting, trading logic, production deployment infrastructure.
