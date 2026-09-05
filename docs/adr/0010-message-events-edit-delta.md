# ADR 0010 — Message Events and Edit Delta

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §9

## Context

Provider messages have their own lifecycle: they are created,
edited, deleted, and may arrive as follow-ups. This lifecycle
is separate from Signal lifecycle (`LifecycleState` in
`packages.signal_core.enums`). A message edit does not set a
Signal to a new lifecycle state; a message deletion does not
directly set a Signal to CANCELLED.

## Decision

Message events are an explicit closed enum:

```text
MessageEvent = CREATE | EDIT | DELETE | FOLLOW_UP
```

An edited message is reparsed from its latest text and
represented as an `EditDelta` (added / changed / removed /
unchanged `ParsedFragment`s). The parser does NOT apply
revisions in Phase 2; it produces the delta.

A deleted message yields `NO_SIGNAL` with evidence
`message_deleted` and a `CorrelationRequest DELETE_APPLY`.

Message lifecycle and Signal lifecycle are never conflated:
a message event never directly sets `LifecycleState`.

## Consequences

Positive:

- Edits are represented as deltas, auditable and replayable.
- Deletion is deterministic and does not invent a signal.
- Follow-ups are explicit (`FOLLOW_UP` + correlation request).
- Phase 1 lifecycle invariants are preserved.

Negative:

- Edit-delta computation requires the correlation layer to
  compare fingerprints (deferred to Phase 3+).
- The parser alone cannot decide whether an edit produces a
  `SignalRevision`.

Reversibility: medium. The `EditDelta` shape is internal; the
IR surface can remain stable.
