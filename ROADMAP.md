# ROADMAP

## What's Happened
- Phase 2A–2F parser implementation (contract layer, engine, provider profiles 001–017, real-corpus batch 1, safety hardening, multi-block ADR 0013, adversarial audit) was built in prior sessions and — after a read-only reconciliation audit found it uncommitted with stale authoritative docs — was formally ADOPTED by an explicit owner decision on 2026-09-05.

## What's Done (Current Session)
- Implemented design §25 step 5: `packages/parser/output_adapter.py` (ParseResult → Signal | SignalInstruction | explicit NON_SIGNAL; caller-supplied `SignalIdentity` + symbol→`Instrument` mapping; missing trigger → UNSPECIFIED, never MARKET; representational conflicts surfaced as stable NON_SIGNAL reasons — MARKET geometry with preserved entry (M24-class) and range SL; lossless action payloads per §20.10–§20.15; MULTI_SIGNAL aggregates refused per ADR 0013 §5) + 35 focused tests in `tests/parser/contract/test_output_adapter.py`.
- Reconciled governance: `docs/phase-status.md` (Phase 2 IMPLEMENTATION COMPLETE, adopted scope; adoption record; deferrals; M24 conflict), `docs/architecture.md`, `README.md`, design §25/§26.1 (MULTI_SIGNAL registry note), ADR 0013 status (owner adoption recorded), `docs/roadmap.md` pointer; removed stale `report.txt`.
- Verified: 940 tests pass (905 prior + 35 adapter; unit subset 334 intact; parser subset 606), ruff check clean, mypy clean (33 files), format drift unchanged (16 pre-existing files). Reconciliation commit created locally; NOT pushed (awaiting owner release approval).

## What's To Be Done
- Owner decisions pending: push/release approval; MULTI_SIGNAL capability enforcement (ADR 0013 deviation #9); M24-class MARKET-geometry-with-entry representability (Phase 1 model extension ADR or Phase 3 correlation-side handling); corpus batch-2 (M14/M15/M18/M29/M28); remaining design §23 open questions.
- Phase 3 (correlation, Telegram/Discord ingestion, broker adapters, execution) NOT started, NOT approved.
