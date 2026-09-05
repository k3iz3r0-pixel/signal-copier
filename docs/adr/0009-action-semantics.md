# ADR 0009 — Action Semantics (Semantic Instructions, Not Orders)

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §8

## Context

Provider messages express actions (close fully, close half,
breakeven, move SL, cancel pending, trigger pending, etc.).
These must be represented as semantic instructions, NOT as
broker orders. The parser must not evaluate broker or account
state (e.g., whether the trade is actually in profit).

## Decision

Actions map to existing `InstructionType` members already
present in `packages.signal_core.enums` (Phase 1):

```text
OPEN, MODIFY, CANCEL, CLOSE, PARTIAL_CLOSE, MOVE_SL,
MOVE_TP, BREAKEVEN, TRAIL, SCALE_IN, SCALE_OUT, REVERSE
```

No new `InstructionType` members are introduced by the parser.

Conditions such as "only if the trade is in profit" are
represented as deterministic `Condition` predicates
(`IN_PROFIT`, `AT_PRICE`, `KEYWORD_PRESENT`, `NONE`). The
parser RECORDS conditions; it never evaluates them. Broker /
account state evaluation is explicitly out of scope for the
parser.

`TRIGGER_PENDING` remains an open question: represent as
`MODIFY` with a `trigger_pending` flag, or as a future
`InstructionType`. Deferred (see design doc §23).

## Consequences

Positive:

- The parser stays broker-agnostic and stateless.
- Conditions are auditable and deterministic.
- No new enums; Phase 1 contract preserved.
- Execution/strategy layers own condition evaluation.

Negative:

- A consumer must know that `PARTIAL_CLOSE` with percent
  carries `partial_close_percent`, not a broker quantity.
- Condition evaluation is deferred to a later phase; until
  then conditional actions are represented but not acted on.

Reversibility: high. The action→InstructionType mapping is a
single table in the OUTPUT ADAPTER.
