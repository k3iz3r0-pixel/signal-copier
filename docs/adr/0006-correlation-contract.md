# ADR 0006 — Correlation Contract

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §9-§11

## Context

Provider messages often arrive in sequences:

- A multi-message signal: "BUY EURUSD" → "@ 1.1000" → "SL 1.0950" → "TP 1.1100".
- A follow-up modification: signal at T0, then "SL 1.0940" at T1.
- An edit: signal at T0, then edit at T1 with a different SL.
- A deletion: signal at T0, then deletion at T1.
- A reply: comment at T0 in reply to a signal at T-1.

The parser must NOT invent a "new signal" from a follow-up
like "SL 3320". The parser also must NOT silently merge a
follow-up into the most recent signal without evidence.

Yet the parser must not implement the full correlation
graph either — that's a separate concern, in a separate
phase, with its own tests.

## Decision

The parser is **single-message-scoped** for parsing but
explicitly produces a `CorrelationRequest` describing what
the correlation layer must do. The parser does NOT correlate.

The parser output separates five layers:

```text
A. lexical parsing     (RawMessage -> tokens/candidates)
B. semantic parsing    (candidates -> ParsedFragments)
C. signal correlation  (Phase 3+)
D. revision generation (Phase 3+)
E. instruction generation (OUTPUT ADAPTER)
```

For a message that is a follow-up (e.g., "SL 3320" with no
direction, no instrument, no other context):

- The parser returns `NO_SIGNAL` with evidence
  `follow_up_only`.
- The IR carries a `ParsedFragment` for the SL and a
  `CorrelationRequest` `TARGET_LAST_SIGNAL`.
- `MessageMetadata.reply_to` (`ContextReference`) is
  preserved for the correlation layer.

The correlation layer (Phase 3+) receives the `ParseResult`
plus context and decides:

- Is this a new signal?
- Is this a follow-up to a recent signal?
- Is this an edit of a recent message?
- Is this a deletion of a recent message?

The correlation contract is **not** implemented in Phase 2
design. Phase 2 design only defines:

- `MessageMetadata.reply_to` / `ContextReference` (the
  relationship is recorded).
- `CorrelationRequest` kinds (TARGET_LAST_SIGNAL,
  TARGET_REPLIED_SIGNAL, MULTI_MESSAGE_APPEND, EDIT_APPLY,
  DELETE_APPLY, NONE).
- `message_event` (`CREATE` / `EDIT` / `DELETE` /
  `FOLLOW_UP`) and `EditDelta`.

The correlation layer is responsible for:

- Holding the recent-message state.
- Resolving `ContextReference`s.
- Replaying edited messages (re-parsing the latest text and
  comparing fingerprints).
- Detecting deletions and issuing `CANCELLED` events.
- Attaching a follow-up to a prior signal.

The parser does not do any of this. The contract is the
boundary: parser produces `ParseResult`; correlation consumes
`ParseResult` + context.

## Consequences

Positive:

- The parser remains single-message-scoped and pure.
- The correlation layer is a separate, testable subsystem.
- The parser does not depend on a "current signal" state.
- The parser is trivially parallelizable (each message is
  independent).

Negative:

- A pure single-message parser cannot produce a `Signal`
  for a multi-message sequence on its own. The correlation
  layer is required for the full flow.
- The correlation contract is deferred; the design document
  has open questions on edit semantics, deletion
  propagation, and reverse identity policy.

Reversibility: high. Adding correlation to the parser is
the wrong direction; the correlation layer remains
external.
