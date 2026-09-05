# Signal → Canonical Snapshot → SignalRevision — Contract

This document describes the **future contract** for obtaining a complete
deterministic representation of a `Signal` suitable for persistence and replay.

**Phase 1.1 — documentation only. NO implementation is provided.**

## Status

```text
Contract status:   DOCUMENTED (not implemented in Phase 1 or Phase 1.1)
Implementation:    DEFERRED to a future phase (after Phase 1.1 freeze is approved)
Serialization:     NOT in scope. No serialization framework dependency.
```

## Contract Flow

```text
Signal
  │
  │  canonical projection (pure function, deterministic)
  ▼
canonical snapshot (frozen tuple of (str, object) pairs)
  │
  │  embedded in SignalRevision.canonical_snapshot
  ▼
SignalRevision
  │
  │  fingerprint = SHA-256(canonical_fingerprint(snapshot))
  ▼
audit chain (linked by previous_revision_id)
```

## Signal → Canonical Snapshot (Projection)

The projection is a **pure function** that converts a `Signal` instance into
a `canonical_snapshot` suitable for embedding in `SignalRevision.canonical_snapshot`.

```python
def project_signal_to_canonical_snapshot(
    signal: Signal,
) -> tuple[tuple[str, object], ...]: ...
```

Properties:

- **Pure**: no side effects, no I/O, no global state.
- **Deterministic**: the same `Signal` always produces the same snapshot.
- **Total**: defined for every valid `Signal` (no partial output).
- **Independent of identity metadata**: the snapshot must NOT include
  `logical_signal_id`, `revision_id`, `revision_number`,
  `previous_revision_id`, `event_reference_id`, or `created_at_utc`. These
  are revision metadata, not semantic content.
- **Order-preserving at the field level**: the snapshot is a tuple of
  `(str, object)` pairs; the field order is canonical (defined by the
  projection function) and must not vary between runs.
- **Tuple ordering semantic**: when the signal contains tuple-typed values
  (e.g., `entry_levels`, `take_profit_targets`), their order is semantic
  and must be preserved (BUY ascending, SELL descending, MULTIPLE
  ascending — see design §10, §20, `invariants.py`).

## Canonical Snapshot Field Set (Authoritative)

The snapshot is a tuple of `(str, object)` pairs covering the full semantic
state of the `Signal` at a point in time:

| Field                  | Source on Signal                  | Normalized form              |
|------------------------|-----------------------------------|------------------------------|
| `direction`            | `signal.direction`                | enum value string            |
| `entry_geometry`       | `signal.entry_geometry`           | enum value string            |
| `entry_trigger`        | `signal.entry_trigger`            | enum value string            |
| `entry_price`          | `signal.entry_price`              | `Price` (frozen) or `None`   |
| `entry_range`          | `signal.entry_range`              | `PriceRange` (frozen) or `None` |
| `entry_levels`         | `signal.entry_levels`             | `tuple[Price, ...]`          |
| `stop_loss`            | `signal.stop_loss`                | `Price` (frozen) or `None`   |
| `take_profit_targets`  | `signal.take_profit_targets`      | `tuple[Price, ...]`          |
| `instrument`           | `signal.instrument`               | `Instrument` (frozen)        |
| `status`               | `signal.status`                   | enum value string            |
| `lifecycle_state`      | `signal.lifecycle_state`          | enum value string            |

Excluded from the snapshot (revision metadata only):

- `identity.logical_signal_id` — independent of content; used for chain
  linking, not for change detection.
- `identity.provider_identity` / `identity.source_identity` — provenance
  metadata, separate from signal content.
- `revision_reference_id` — reference to the current revision, not content.
- `created_at_utc` — timestamp metadata.

## Canonical Snapshot Validation

The snapshot must conform to the unified `ALLOWED_SNAPSHOT_TYPES` contract
shared by `SignalRevision`, `SignalEvent.event_payload`,
`SignalInstruction.payload`, and `canonical_fingerprint`. See
`packages/signal_core/domain.py` for the authoritative type list.

Rejection rules (already enforced):

- Duplicate keys in the snapshot tuple: rejected (key uniqueness is required
  for unambiguous canonical representation).
- Mutable collections (list, dict, set, frozenset): rejected at any depth.
- `float`: rejected (financial-number policy; use `Decimal`).
- Unsupported enum types (`SourceType`, `EventType`, `InstructionType`,
  `AssetClass`): rejected (these are not part of the canonical Signal
  semantic surface).
- Custom objects: rejected.

## Canonical Snapshot → SignalRevision

The snapshot is embedded in `SignalRevision.canonical_snapshot` as the
`canonical_snapshot` field (frozen tuple of `(str, object)` pairs). The
revision carries:

- `revision_id` (unique per snapshot, non-deterministic)
- `logical_signal_id` (stable across revisions)
- `revision_number` (monotonic, starting at 1)
- `previous_revision_id` (links to the prior revision; `None` for first)
- `canonical_snapshot` (the projection result)
- `fingerprint` (derived from `canonical_snapshot` via `canonical_fingerprint`)
- `event_reference_id` (optional, references the producing `SignalEvent`)
- `snapshot_version` (reserved for future format evolution)
- `created_at_utc`

The fingerprint is **always** recomputed from the snapshot and is never
trusted from caller input (see `SignalRevision.__post_init__`).

## SignalRevision Does Not Recursively Embed Signal

`SignalRevision.canonical_snapshot` is a **flat, non-recursive** frozen
mapping. It MUST NOT contain a full `Signal` instance or any embedded
domain-object graph. Reconstructing a Signal from a revision is a
**future** operation that will live in a downstream layer (e.g., replay),
not in Phase 1.

## What This Document Does Not Authorize

- No implementation in Phase 1 or Phase 1.1.
- No serialization framework dependency.
- No parser, no provider adapter, no broker adapter, no Telegram, no
  Discord, no database, no Redis, no execution, no strategy, no risk, no
  replay engine, no backtesting, no analytics, no AI.
- No recursive ownership between `Signal` and `SignalRevision`.

## Open Questions Deferred to Future Phases

- Whether the projection function should be exposed as a public API.
- How to reconstruct a `Signal` from a `canonical_snapshot` (round-trip
  semantics).
- How to evolve the snapshot format (use `snapshot_version`).
- Whether projection includes any `Signal` fields not listed above.
- Storage representation (out of scope; deferred to a database phase).
