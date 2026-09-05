# ADR 0003 — Message Model Without Ingestion

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §5, §9

## Context

The parser must be testable without Telegram, Discord, brokers,
or any ingestion platform. The parser pipeline must be
implementable in pure Python with no provider SDK dependencies.
Yet the parser must still receive enough information about a
message to disambiguate edits, deletions, replies, and
multi-message signals.

A common antipattern is to leak Telegram-specific fields
(channel ID, chat ID, user ID, message ID format) into the
parser's input. This couples the parser to one ingestion
platform.

## Decision

The parser's message input is split into two provider-agnostic
frozen dataclasses: `RawMessage` (the payload) and
`MessageMetadata` (identity/lifecycle).

`RawMessage`:

- `raw_text: str` (preserved verbatim; never mutated)
- `media_refs: tuple[MediaKind, ...]` (IMAGE / VIDEO / DOCUMENT /
  NONE)
- `raw_payload_hash: str` (SHA-256 of raw_text, for dedup)

`MessageMetadata`:

- `provider_name: str` (e.g., "provider_alpha"; not Telegram-specific)
- `source_type: SourceType` (TELEGRAM / DISCORD / MANUAL / API)
- `source_reference: str | None` (provider-side message ID)
- `timestamp_utc: datetime`
- `message_event: MessageEvent` (CREATE / EDIT / DELETE / FOLLOW_UP)
- `reply_to: ContextReference | None`
- `provenance_extra: tuple[tuple[str, object], ...]`

`DESIGN DECISION` — payload and identity are separated so the raw
payload can be preserved/hashed without being entangled with
source-specific fields. Message lifecycle (`message_event`) is
separate from Signal lifecycle (Phase 1 `LifecycleState`).

The parser does NOT import any provider SDK. Future Telegram /
Discord / API adapters (Phase 3+) translate provider messages
into `RawMessage` + `MessageMetadata` BEFORE the parser sees
them.

`raw_payload_hash` (SHA-256 of `raw_text`) is a
message-identity/dedup hash. It is DISTINCT from the canonical
semantic fingerprint (SHA-256 of the canonical snapshot). The
parser never uses `raw_payload_hash` as a semantic fingerprint,
and never uses the canonical fingerprint for raw-message dedup.

Media policy: the parser NEVER opens, fetches, decodes, or
follows media references or URLs. Text present and parseable →
parse the text and record `media_present` evidence (unopened).
No text but media present → `UNSUPPORTED` with evidence
`media_only_unopened` (no signal invented, payload unopened).
No text and no media → `NO_SIGNAL`.

The architectural boundary is enforced by a boundary test
(Phase 3+):

```python
FORBIDDEN_IMPORTS = {
    "telegram",
    "telethon",
    "pyrogram",
    "discord",
    "mt4",
    "mt5",
    "ctrader",
    "dxtrade",
    "tradelocker",
}
```

Any parser module that imports from these packages fails the
build.

## Consequences

Positive:

- Parser is testable in pure Python with no external SDK.
- A new ingestion platform (e.g., a custom REST API) is a new
  adapter module, not a parser change.
- Parser code is portable; ingestion code is not.
- Architectural boundary is testable.

Negative:

- The `provenance_extra` field is a "loose" escape hatch.
  Mitigated by validation against `ALLOWED_SNAPSHOT_TYPES`
  when the IR is eventually serialized.
- Ingestion adapters must maintain the contract of
  `RawMessage` / `MessageMetadata` translation. The contract
  is large (message_event, reply_to, media presence).

Reversibility: high. The `RawMessage` / `MessageMetadata`
shapes can evolve incrementally; adding a field is non-breaking.
