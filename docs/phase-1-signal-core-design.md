# Phase 1 — Signal Core Design Document

Status: Design document only. No Python domain classes, parser, Telegram,
broker, strategy, risk, execution, database, or AI code implemented.

Phase reference: See docs/architecture.md, AGENTS.md, and approved phase
markers. This design applies to Phase 1 — Signal Core.

## 1. Design Goals and Non-Goals

Goals:
- Define the canonical domain model for trading signals independent of any
  ingestion platform (Telegram, Discord), broker (MT4/MT5, cTrader,
  DXTrade, TradeLocker), database, or AI inference system.
- Define immutable objects (Signal, SignalEvent, SignalRevision) that
  serve as contracts between future parser, provider engine, signal state
  machine, strategy engine, risk engine, execution engine, analytics, and
  replay/backtesting systems.
- Support BUY/SELL, MARKET, single-price, range, and multiple entry
  levels; single and multiple TP targets; partial close; signal
  modifications; cancellation; multi-message reconstruction; partial and
  ambiguous signals.
- Ensure deterministic identity, auditability via revision history, and
  immutability.
- Provide explicit distinction between Signal, SignalEvent,
  SignalRevision, ExecutionIntent, Order, and Position.

Non-Goals (deliberately deferred):
- Parser implementation.
- Telegram/Discord adapter implementation.
- Broker adapter or API integration.
- Strategy engine logic.
- Risk engine calculations (lot sizing, exposure limits).
- Execution engine logic.
- Database schema or persistence layer.
- Redis integration.
- AI inference in any path.
- Serialization/deserialization framework (strategy proposed but not
  implemented).
- Full validation framework (invariants defined, validator not
  implemented).

## 1.5 Information Preservation Principle

The canonical model must preserve all semantically meaningful information
known from the source while never inventing information that was not present.

Rules:
- If the provider specifies direction + price + trigger (e.g., BUY LIMIT @
  1.1000), the Signal must retain direction=BUY, geometry=SINGLE,
  trigger=LIMIT, entry_price=Price("1.1000").
- If the provider provides only direction + price without trigger semantics
  (e.g., "BUY 3350"), the Signal must set trigger=UNSPECIFIED (not MARKET).
  The adapter/parser must not promote UNSPECIFIED to MARKET.
- "BUY MARKET" must only be assigned when provider/source semantics
  explicitly establish market execution.
- "BUY STOP @ 1.1000" must retain trigger=STOP and geometry=SINGLE (or
  appropriate geometry). The parser must not discard STOP semantics.
- Unknown values must remain distinguishable from absent or zero. A missing
  TP must be represented as an empty tuple (explicit absence), not as an
  invented default price.
- Partial/incomplete signals must not be promoted to COMPLETE by inventing
  missing fields. Multi-message reconstruction must preserve the exact
  sequence of partial messages through revision events.
- Provider-specific syntax conversion (adapter layer) must translate syntax
  into canonical fields without discarding semantic distinctions (e.g., LIMIT
  vs STOP vs UNSPECIFIED).

## 2. Complete Domain Model

The domain is organized into six concepts:

A. Signal — the canonical contract object describing a trading signal at
   a point in time.
B. SignalEvent — immutable lifecycle event (created, modified, revised,
   cancelled, etc.).
C. SignalRevision — immutable audit snapshot of Signal at a specific point.
D. ExecutionIntent — abstract contract representing what the execution
   engine should attempt (derived from Signal, not implemented in Phase 1).
E. Order — abstract representation of an order request (downstream,
   interface only in Phase 1).
F. Position — abstract representation of an open position (downstream,
   interface only in Phase 1).

## 3. Every Proposed Domain Object

### 3.1 SignalIdentity (Value Object)

Purpose: Reference to the stable logical signal identity and current
revision context.

Fields:
- logical_signal_id: UUID (required; stable across revisions; never derived
  from mutable canonical content; derived from provider reference/stable
  ingestion reference, not from content hash).
- provider_identity: ProviderSource (required; provider provenance).
- source_identity: SourceIdentity (optional; ingestion source reference).

Note: fingerprint and content hash are separate concepts tracked at the
revision or signal snapshot level (SignalRevision); SignalIdentity does not
include fingerprint, revision_number, or any mutable content. Content fingerprint
is used for dedup/change detection, not identity. Revision sequence information
belongs to SignalRevision, not SignalIdentity.

Type details:
- UUID, ProviderSource, SourceIdentity.
- Required: logical_signal_id, provider_identity.
- Optional: source_identity.

Immutability: Frozen. Logical identity never changes; identity object is
replaced only when a new logical identity is required (new signal, not new revision).

Relationships:
- References the same logical signal across all revisions.
- Separate from SignalRevision identity (revision_id) and content fingerprint.
- Separate from Signal content; identity does not embed Signal fields.

Stable identity rules:
- Provider provides stable signal_reference: logical_signal_id derived from
  provider_identity + normalized provider reference.
- Provider does not provide stable reference: adapter generates logical
  identity deterministically (adapter policy must be documented); same
  ingestion must yield same identity.
- Changing canonical content (e.g., SL moved) updates fingerprint and
  produces new SignalRevision; logical_signal_id remains unchanged.

### 3.1.5 Instrument (Value Object)

Purpose: Provider-agnostic instrument identity required by the canonical
Signal model.

Fields:
- canonical_symbol: str (required; normalized symbol, e.g., "EURUSD").
- asset_class: AssetClass enum (required).

Type details: str, AssetClass enum.
Immutability: Frozen. No mutable fields.
Relationships: One Instrument per Signal (1:1). Independent of provider
adapter details.

Separation from provider/broker mapping:
- Provider-specific symbol mappings (e.g., broker symbol "EURUSDmicro",
  Telegram label "EURUSD") belong to a separate adapter/resolver layer,
  not to Instrument.
- Instrument represents only the provider-agnostic identity of the traded
  asset; adapter/resolver translates between canonical_symbol and
  provider-specific representations when needed by ingestion or execution.

Reason: Keeping provider mappings out of the core Instrument prevents adapter
pollution and ensures the Signal core remains independent of any broker or
provider syntax.

Note: Multi-instrument signals deferred; Phase 1 assumes single instrument
per Signal.

Reason: Instrument is not deferred. The Signal core must reference an
instrument to distinguish signals for different assets without relying on
provider adapter interpretation.

### 3.2 ProviderSource (Value Object)

Purpose: Provider and ingestion provenance without polluting domain with
provider-specific syntax.

Fields:
- provider_name: str (e.g., "provider_alpha", not Telegram-specific).
- signal_reference: str (provider's native reference/ID).
- ingestion_timestamp_utc: datetime (optional; unknown allowed for
  multi-message partial signals).

Type details: str, str, Optional[datetime].
Immutability: Frozen.

### 3.3 SourceIdentity (Value Object)

Purpose: Ingestion source identity separate from provider identity.

Fields:
- source_type: SourceType enum (e.g., TELEGRAM, DISCORD, MANUAL, API).
- source_reference: str (optional message/chat/reference ID from source).
- ingestion_timestamp_utc: Optional[datetime].

Type details: SourceType enum, str, Optional[datetime].
Immutability: Frozen.
Note: SourceType enum references possible ingestion platforms by generic
type only. No Telegram-specific logic lives in core.

### 3.4 Price (Value Object)

Purpose: Financial price representation with strict decimal precision.

Fields:
- value: Decimal (required; must be a valid Decimal; never None inside
  Price; None is represented by the absence of the Price object at the
  containing field level, not by Price(value=None)).
- currency: Optional[str] (optional for Phase 1; reserved for multi-currency
  contexts).

Type details: Decimal; float is banned from domain.
Immutability: Frozen. Hashable. Comparable.
Unknown value representation: containing field = None (Price | None), not
Price(value=None).
Explicit zero: Price(value=Decimal("0.0")) is a meaningful price.
Absent: containing field set to None.
Ambiguous price: cannot be represented by Price alone; ambiguity requires
SignalStatus.AMBIGUOUS or partial/incomplete event, not a special Price value.

### 3.5 PriceRange (Value Object)

Purpose: Entry range with low/high boundaries.

Fields:
- low: Optional[Price] (must be present for RANGE; None for MARKET or
  unknown).
- high: Optional[Price] (required when range is used; low <= high must
  hold when both present).

Type details: Optional[Price], Optional[Price].
Immutability: Frozen.
Invariant (defined but not enforced in Phase 1): when both present,
low.value <= high.value.

### 3.6 TradeDirection (Enum)

Purpose: Trade direction.

Members: BUY, SELL.
Reason: Fundamental geometric invariant depends on direction (BUY: SL <
entry, TP >= entry; SELL: SL > entry, TP <= entry). No ambiguous direction.
No REVERSAL member: reversal is an event/modification type, not a
direction override.

### 3.7 EntryGeometry (Enum) — Geometry Only

Purpose: How the entry is structured geometrically.

Members:
- MARKET: market entry (entry price unknown at signal time).
- SINGLE: single price entry.
- RANGE: entry range (low/high boundaries).
- MULTIPLE: multiple entry levels (MULTIPLE_LEVELS; ordered tuple of Price
  objects; strategy/execution determines whether these represent scale-in,
  staggered entries, averaging, or other multi-level strategies).

Reason: Separate from execution/order semantics (LIMIT, STOP, MARKET as
execution order types). Signal represents the canonical trading idea; the
execution layer (ExecutionIntent) translates entry geometry into specific
execution instructions. This prevents broker-specific execution semantics
from polluting the core domain.

Execution semantics (LIMIT, STOP, MARKET as order types, UNSPECIFIED) are
separate from geometry and belong to a distinct concept (see Section 3.7.5
EntryTrigger / Section 8 revision). The Signal domain preserves both geometry
and trigger semantics without conflating them.

### 3.7.5 EntryTrigger (Enum) — Execution/Trigger Semantics

Purpose: How the entry should be triggered/executed, independent of geometry.

Members:
- MARKET: market execution at best available price.
- LIMIT: limit order at specified price.
- STOP: stop order at specified price.
- UNSPECIFIED: provider did not specify execution semantics; must not be
  defaulted to MARKET; preserves absence of information.

Reason: Separates the geometric form of the entry (what price/levels) from
execution semantics (how the broker should execute it). A single geometry
(SINGLE) may have any trigger (LIMIT, STOP, MARKET, UNSPECIFIED). The
canonical model must preserve all combinations (BUY LIMIT @ price,
BUY STOP @ price, BUY MARKET, BUY UNSPECIFIED) without inventing MARKET
when only a price is given.

Unknown vs unspecified:
- UNSPECIFIED is a distinct value from MARKET. A provider message giving
  only direction and price must not be promoted to MARKET; it must remain
  UNSPECIFIED unless the adapter/provider syntax establishes MARKET.
- MARKET is only assigned when provider/source semantics explicitly indicate
  market execution.

### 3.8 LifecycleState (Enum)

Purpose: Minimal deterministic lifecycle state of the signal.

Members:
- DRAFT: initial construction; partial or ambiguous allowed.
- ACTIVE: complete or actionable partial signal.
- CANCELLED: signal explicitly cancelled.
- EXPIRED: signal reached time/validity expiration (optional terminal state before ARCHIVED).
- ARCHIVED: terminal audit state.

Reason: The signal lifecycle describes only the canonical signal state.
Execution activity (EXECUTING, EXECUTED, PARTIAL_CLOSE, CLOSE_COMPLETE,
SCALE_OUT) is tracked by downstream ExecutionIntent / Order /
ExecutionResult / Position models, not by Signal lifecycle. Removing
EXECUTING and EXECUTED keeps the signal lifecycle independent of any
single execution outcome and prevents invalid cross-domain state coupling.

Life cycle (minimal):
DRAFT -> ACTIVE -> CANCELLED / EXPIRED -> ARCHIVED

Note: CANCELLED and EXPIRED are terminal except for ARCHIVED; no transition
back to ACTIVE. EXECUTING and EXECUTED are removed as persistent signal
lifecycle states; they exist as event categories (see Section 3.10) that
reference the signal identity.

Signal lifecycle vs execution lifecycle separation:
- Signal lifecycle (DRAFT, ACTIVE, CANCELLED, ARCHIVED) describes the state
  of the canonical signal idea: whether it is being constructed, actionable,
  cancelled, or archived.
- Execution lifecycle (EXECUTING, EXECUTED) describes downstream execution
  activity linked to the signal through ExecutionIntent, not the signal's
  own state. The same Signal may be referenced by multiple ExecutionIntents
  (e.g., copied to different accounts/brokers) with different execution
  results. Therefore EXECUTING and EXECUTED are events (SignalEvent types)
  that reference the signal, not persistent lifecycle states of the Signal
  itself. The Signal remains ACTIVE through execution unless execution
  results in explicit cancellation or modification events.
- This separation ensures the Signal core remains independent of any single
  global execution outcome.

### 3.9 SignalStatus (Enum)

Purpose: Completeness and ambiguity status of the signal content itself.

Members: PARTIAL, COMPLETE, AMBIGUOUS.

Reason:
- PARTIAL: some fields (e.g., TP) missing intentionally; parser did
  not invent them; multi-message reconstruction in progress.
- COMPLETE: all required fields for a given representation present.
- AMBIGUOUS: syntax unclear; parser could not determine entry type,
  direction, or price relationships; no silent promotion.

This ensures no silent handling of malformed/ambiguous signals.

### 3.10 EventType (Enum) — Separated Categories

Purpose: Types of events, separated by domain concept to prevent mixing
signal lifecycle, modification, execution, and position events.

Signal lifecycle events (signal creation/state):
- CREATED
- CANCELLED
- ARCHIVED (if added to lifecycle events; currently lifecycle state only)
- INCOMPLETE_SIGNAL_RECEIVED

Signal modification/revision events (produce new SignalRevision):
- REVISED (new revision from content change or multi-message completion)
- SL_MOVED
- TP_MOVED
- BREAKEVEN
- SCALE_IN (entry levels expanded; may or may not change revision)
- REVERSAL (direction change event)

Execution-related events (downstream activity; reference signal identity,
not embedded Signal):
- EXECUTING
- EXECUTED
- PARTIAL_CLOSE
- CLOSE_COMPLETE
- SCALE_OUT

Note: MODIFIED is removed as a separate event type (REVISED covers
revision-producing changes); PARTIAL_CLOSE and CLOSE_COMPLETE are
execution events linked to ExecutionIntent, not signal modification events;
SCALE_IN is a signal modification (entry levels expanded), SCALE_OUT is
an execution/position event.

Reason: Separating categories prevents using a single enum as a dumping
ground for unrelated concepts. It clarifies which events change Signal
state/revisions, which are downstream execution events, and which are
signal instructions (SignalAction).

### 3.11 Signal (Domain Object — Frozen Dataclass)

Purpose: Canonical contract describing a trading signal.

Fields:
- identity: SignalIdentity (required).
- instrument: Instrument (required; single instrument per signal in Phase 1).
- direction: TradeDirection (required; BUY or SELL).
- entry_geometry: EntryGeometry (required; MARKET, SINGLE, RANGE, MULTIPLE).
- entry_trigger: EntryTrigger (required; MARKET, LIMIT, STOP, UNSPECIFIED; never defaulted to MARKET).
- entry_price: Optional[Price] (Price | None; required for SINGLE; None for MARKET; may be None for RANGE/MULTIPLE).
- entry_range: Optional[PriceRange] (present for RANGE; None for others; PriceRange frozen with Optional[Price] fields).
- entry_levels: tuple[Price, ...] (frozen tuple; present for MULTIPLE; empty tuple for others; ordered; never mutable list).
- stop_loss: Optional[Price] (Price | None; None indicates explicitly absent).
- take_profit_targets: tuple[Price, ...] (frozen tuple; ordered; empty tuple for no TP; never mutable list; never None at container level — empty tuple = absent; individual target is Price object, never None inside tuple).
- status: SignalStatus (required; PARTIAL, COMPLETE, or AMBIGUOUS).
- lifecycle_state: LifecycleState (required; minimal deterministic machine: DRAFT, ACTIVE, CANCELLED, EXPIRED, ARCHIVED; see Section 14).
- revision_reference_id: Optional[UUID] (optional reference to current SignalRevision by ID; not embedded object; prevents recursive ownership).
- created_at_utc: datetime (required; immutable timestamp of signal creation, not ingestion time).

Type details: All domain types defined above; Decimal for Price values.

Immutability: Frozen dataclass. Any change produces a new Signal instance
with a new SignalRevision; original Signal remains unchanged.

Relationships:
- Owns SignalIdentity (1:1).
- References SignalRevision (optional 1:1 for audit chain).
- Produces SignalEvent instances (1:N over lifecycle).
- Independent of ExecutionIntent, Order, Position.

### 3.12 SignalRevision (Domain Object — Frozen Dataclass)

Purpose: Immutable audit snapshot of Signal state at a point in time.
A revision must be independently inspectable without replaying previous
events or referencing a separate Signal object.

Fields:
- revision_id: UUID (required; unique snapshot ID).
- logical_signal_id: UUID (required; stable logical identity; never changes
  across revisions; completely independent of mutable content).
- revision_number: int (required; monotonic sequence starting at 1 for the
  first revision; increments with each new revision; separate from logical identity).
- previous_revision_id: Optional[UUID] (None only for the first revision;
  links revisions into a non-recursive singly-linked chain).
- canonical_snapshot: frozen_mapping_type (required; full canonical state
  needed to reconstruct the signal at this revision; includes all semantic
  fields: direction, entry_geometry, entry_trigger, entry_price, entry_range,
  entry_levels, stop_loss, take_profit_targets, instrument reference,
  status, lifecycle_state, and any other canonical fields. It is a frozen,
  non-recursive mapping — never embeds a full Signal instance, never embeds
  mutable collections. It captures the complete semantic trading information
  at this point, not just fingerprints of selected fields, so a revision can
  be inspected independently).
- fingerprint: str (required; canonical content hash of the snapshot fields;
  excludes revision metadata: revision_id, logical_signal_id, revision_number,
  previous_revision_id, event_reference_id, created_at_utc. Changes when
  canonical content changes; identical for duplicate content; different for
  any content change).
- event_reference_id: Optional[UUID] (reference to the SignalEvent that
  produced this revision; not an embedded SignalEvent object).
- snapshot_version: int (optional; snapshot schema version; reserved for
  future format evolution).
- created_at_utc: datetime (required).

Snapshot immutability:
- canonical_snapshot is a frozen mapping (frozen_mapping_type) constructed
  from the canonical fields at revision time. Once created it is never
  mutated; any "modification" creates a new SignalRevision with a new
  canonical_snapshot.
- No embedded Signal, SignalEvent, or mutable collections inside the snapshot.
- The fingerprint is computed from the canonical_snapshot contents (normalized,
  deterministic serialization of the frozen mapping) and stored as a string.

Fingerprint calculation:
- Computed from canonical_snapshot fields (semantic trading content) only.
- Excludes identity and revision metadata (logical_signal_id, revision_number,
  previous_revision_id, revision_id, event_reference_id, created_at_utc).
- Normalized: all Decimal values serialized as normalized strings; all tuples
  ordered deterministically; frozen mappings sorted by key; no provider_metadata.
- Same snapshot content yields the same fingerprint; different content yields
  different fingerprints (collision-resistant; practical equality for audit).

Revision linking:
- previous_revision_id links to the prior revision of the same logical signal.
- Revisions form a singly-linked list; no branching; no gaps.
- Replay/reconstruction: traverse revisions by previous_revision_id from the
  most recent back to the first; apply canonical_snapshot values in sequence.
  No event replay is required to inspect any individual revision's state.
- A new revision always references the same logical_signal_id; a new logical
  identity creates a separate chain starting at previous_revision_id = None.

Type details: UUID references; frozen snapshot mapping; str fingerprint.
Immutability: Frozen dataclass. Snapshot mapping frozen; no mutation after creation.
Relationships: References logical signal identity (not full Signal); linked list
via previous_revision_id; references producing event by ID only.

### 3.13 SignalEvent (Domain Object — Frozen Dataclass)

Purpose: Immutable audit log entry for signal lifecycle changes.

Fields:
- event_id: UUID (required; unique audit event ID, non-deterministic).
- signal_identity: SignalIdentity (required; reference only, not full Signal).
- event_type: EventType (required).
- timestamp_utc: datetime (required; logical event ordering timestamp).
- previous_revision_id: Optional[UUID] (revision before event, if applicable).
- new_revision_id: Optional[UUID] (revision produced by event, if applicable).
- event_payload: frozen_mapping_type (optional frozen mapping of
  structured event details; e.g., previous SL value reference and new SL
  value reference for SL_MOVED; core does not enforce schema beyond
  event_type; never mutable dict).
- provenance: ProviderSource (optional; ingestion provenance at event time).

Type details: UUID, EventType, datetime, Optional[UUID], Optional[dict].
Immutability: Frozen. Events are append-only.
Relationships: References SignalIdentity; optionally references revisions.

### 3.14 ExecutionIntent (Abstract Contract — Phase 1 Interface Only)

Purpose: Contract defining what the execution engine should attempt,
without broker-specific logic.

Fields (interface definition, not implemented):
- signal_identity: SignalIdentity (required).
- intent_type: IntentType enum (SUBMIT_ORDER, CANCEL_ORDER, MODIFY_ORDER,
  CLOSE_POSITION — proposed but not implemented).
- direction: TradeDirection (required; derived from Signal).
- entry_instructions: List[EntryInstruction] (derived from Signal entry).
- target_instructions: List[TargetInstruction] (derived from TP/SL).
- status: IntentStatus (PENDING, SUBMITTED, FILLED, REJECTED, CANCELLED —
  interface only).

Type details: Abstract; no concrete fields required in Phase 1.
Relationships: Derived from Signal + SignalEvent; independent of Signal
mutation.

Distinction from Signal: Signal describes the trading idea; ExecutionIntent
describes the action the execution system should take.

### 3.15 Order (Abstract Contract — Phase 1 Interface Only)

Purpose: Abstract representation of an order request (downstream contract).

Fields (interface definition):
- order_identity: UUID.
- direction: TradeDirection.
- entry_instructions: abstract list.
- stop_loss_instructions: abstract list.
- target_instructions: abstract list.
- status: OrderStatus.
- broker_reference: Optional[str] (broker-specific reference; core does not
  populate or interpret).

Type details: Interface only. No concrete fields.
Relationships: Produced from ExecutionIntent; independent of Signal.

Distinction: Order is a concrete request format; Signal is the canonical
idea; ExecutionIntent is the bridge.

### 3.16 Position (Abstract Contract — Phase 1 Interface Only)

Purpose: Abstract representation of an open position.

Fields (interface definition):
- position_identity: UUID.
- signal_identity: SignalIdentity (optional; link to originating signal).
- direction: TradeDirection.
- open_quantity: Decimal.
- entry_prices: List[Decimal] (average or per-level tracking).
- current_stop_loss: Optional[Decimal].
- current_take_profit_targets: List[Decimal].
- status: PositionStatus.

Type details: Interface only.
Relationships: Created/updated by execution of orders; can link to
SignalIdentity for audit/replay.

## 4. Complete Enum Definitions and Reasoning

TradeDirection (BUY, SELL): Geometry invariants (entry/SL/TP
relationships) depend on it. Reversal is a modification event type, not a
direction.

EntryGeometry (MARKET, SINGLE, RANGE, MULTIPLE): Separates entry geometry
from direction, enabling independent representation of market entries,
single price entries, ranges, and multiple entry levels (MULTIPLE_LEVELS).

LifecycleState (DRAFT, ACTIVE, CANCELLED, EXPIRED, ARCHIVED):
Minimal deterministic lifecycle tracking for the signal itself. EXECUTING
and EXECUTED are removed; they are downstream execution events, not
persistent signal lifecycle states. MODIFIED and REVISED are event types,
not persistent lifecycle states.

EventType categories (see Section 3.10 for details): signal lifecycle
(CREATED, CANCELLED, INCOMPLETE_SIGNAL_RECEIVED); signal modification
(REVISED, SL_MOVED, TP_MOVED, BREAKEVEN, SCALE_IN, REVERSAL); execution
(EXECUTING, EXECUTED, PARTIAL_CLOSE, CLOSE_COMPLETE, SCALE_OUT). Separated
to prevent mixing unrelated concepts.

SignalStatus (PARTIAL, COMPLETE, AMBIGUOUS): Explicitly distinguishes
incomplete/ambiguous signals. Prevents silent promotion and ensures the
parser must explicitly mark ambiguity.

SourceType (TELEGRAM, DISCORD, MANUAL, API): Generic ingestion platform
reference only; no Telegram-specific logic in core.

## 5. Value Objects and Justification

SignalIdentity: Justified — deterministic identity is required for
deduplication, audit chain linking, and replay. Random UUIDs would
break replay determinism.

ProviderSource: Justified — separates provider provenance from domain.
Without it, provider-specific fields would leak into Signal.

Price: Justified — Decimal is required for financial accuracy; float is
banned. Separate value object enforces this at the type level.

PriceRange: Justified — entry ranges need low/high boundaries with
explicit None for unknown. Without it, range representation would be
ambiguous or require tuple structures.

SourceIdentity: Justified — ingestion source identity may differ from
provider identity (e.g., Telegram bot providing signals from a specific
provider). Keeps separation clean.

Not needed in Phase 1: Currency-specific value objects, quantity object
(Quantity can use Decimal directly with additional constraints in
invariants), execution timestamp tracking (covered by SignalEvent).

## 6. Instrument Representation

Instrument (Instrument value object) IS required in Phase 1 and is part of
Signal (see Section 3.1.5). It contains only provider-agnostic identity:
canonical_symbol and asset_class. Provider-specific symbol mappings belong
to the adapter/resolver layer, not Instrument.

The Signal contract assumes a single instrument per signal; multi-instrument
signals are deferred to future phases.

## 7. Price Representation and Financial-Number Precision Strategy

Strategy:
- All monetary/price values use Python Decimal (not float).
- Float is explicitly banned from domain objects.
- Decimal ensures exact arithmetic for price relationships (e.g., SL <
  entry, TP ordering) without floating-point errors.
- Serialization: Decimal must be serialized as string (not float) in any
  future JSON representation; this is proposed but not implemented.
- Unknown/unavailable price: represented as None (Python NoneType), not
  Decimal("0"). This distinguishes "unknown" from "zero price."
- Explicit zero: Decimal("0.0") is a valid, meaningful price (e.g.,
  breakeven SL at entry price).

Performance: Decimal is slower than float but acceptable for domain
objects; hot-path performance is preserved by avoiding validation in the
hot path and using frozen dataclasses. Note: Decimal provides exact decimal
arithmetic and deterministic representation; it does NOT define market tick
size, broker price precision, or minimum price increments. Those belong to
instrument/execution adapter and broker-specific layers, not the core domain.

## 8. Entry Representation (Geometry, Separate from Execution)

The Signal domain separates entry geometry from execution/order semantics.

Geometry (EntryGeometry enum): MARKET, SINGLE, RANGE, MULTIPLE.
Execution semantics (deferred to ExecutionIntent / adapter): LIMIT, STOP,
MARKET as order types, conditional orders, etc.

Supported entry forms (geometry only):

- MARKET: entry_geometry = MARKET; entry_price = None (unknown at signal
  time); entry_range = None; entry_levels = None / empty tuple.
- SINGLE: entry_geometry = SINGLE; entry_price = Price(value); entry_range
  = None; entry_levels = empty tuple.
- RANGE: entry_geometry = RANGE; entry_price = None; entry_range =
  PriceRange(low, high); entry_levels = empty tuple.
- MULTIPLE: entry_geometry = MULTIPLE; entry_price = None; entry_range =
  None; entry_levels = non-empty tuple of Price objects (ordered).

Quantity/allocation for MULTIPLE: quantity/quantity-allocation belongs to
ExecutionIntent and Strategy/Risk layers, not Signal. The Signal preserves
only the entry level prices present in the provider signal. No execution
quantities are invented in the core domain. If provider provides quantities,
they are preserved in ExecutionIntent or reserved adapter-level fields, not
Signal domain objects.

Unknown/unavailable distinction: entry_price = None (Price | None) means
"unknown or market entry"; empty tuple indicates absence, not zero levels.
EntryGeometry never includes execution order types (LIMIT, STOP); those are
execution semantics handled by adapter and ExecutionIntent.

## 9. Stop-Loss Representation

- stop_loss: Optional[Price].
- None indicates no SL specified (not missing by error, but explicitly
  absent).
- Zero value Decimal("0.0") is meaningful (e.g., SL at zero price for
  certain instruments or strategies).
- SL relationships (invariants):
  - BUY: SL.value < Signal.entry_price.value (when entry_price present).
  - SELL: SL.value > Signal.entry_price.value.
- For MARKET entries: SL value is independent of unknown entry price;
  execution engine handles relationship at fill time.

## 10. Take-Profit Representation

- take_profit_targets: List[Price].
- Empty list: no TP specified.
- None: not used (use empty list for absence; None reserved for
  unknown individual Price objects within targets).
- Multiple targets: ordered list. Ordering invariant proposed but not
  enforced:
  - BUY: ascending order (lowest TP first).
  - SELL: descending order (highest TP first).
- Partial close: future ExecutionIntent splits quantities across TP
  targets; Signal domain reserves target list but does not enforce
  quantity allocation per target in Phase 1.
- Future allocation: reserved but deferred; domain defines targets only,
  not how much quantity closes at each target.

## 11. Signal Identity Strategy

Separation of concerns:

A. Logical Signal Identity (stable across revisions):
- logical_signal_id: UUID (required; stable across revisions; never derived
  from mutable canonical content; derived from provider reference + stable
  provider signal reference, or generated deterministically by ingestion
  adapter if provider does not supply a stable reference).
- Stable identity does NOT change when canonical signal content changes
  (e.g., SL moved, TP added). Changing content creates a new revision, not
  a new logical identity.
- Provider does not supply stable reference case: adapter generates
  logical_signal_id deterministically from ingestion source + message
  reference + timestamp normalization; adapter must document this policy.

B. Signal Identity (SignalIdentity value object):
- logical_signal_id: UUID (required; same as A; never derived from mutable content).
- provider_identity: ProviderSource (required; provider provenance).
- source_identity: SourceIdentity (optional; ingestion source reference).
No revision_sequence here; revision sequence belongs to SignalRevision.

C. Revision Identity (SignalRevision):
- revision_id: UUID (unique per snapshot; required).
- logical_signal_id: UUID (same logical signal; never changes).
- revision_number: int (monotonic sequence; starts at 1 for first revision; increments per new revision).
- previous_revision_id: Optional[UUID] (links previous revision; None only for first).
- canonical_snapshot: frozen snapshot of full canonical state at this revision.
- fingerprint: str (content hash of canonical_snapshot; excludes revision metadata).

D. Content Fingerprint (for dedup and change detection):
- fingerprint: str (canonical hash of normalized Signal content at revision
  time; excludes logical identity fields, event IDs, revision IDs, ingestion
  timestamps, and mutable adapter metadata; changes when canonical content
  changes).
- Deduplication: same logical_signal_id + same fingerprint = duplicate
  (same content, same signal); same logical_signal_id + different
  fingerprint = new revision (same logical signal, changed content).
- Different logical_signal_id = different logical signal, regardless of
  fingerprint similarity.

E. Provider-specific identity case (authoritative rules):
- logical_signal_id is NEVER derived from mutable canonical content.
  It is derived from provider_identity + stable provider signal_reference
  (normalized), or deterministically from ingestion adapter policy.
- Changing canonical content (e.g., SL moved, TP added, entry changed) does
  NOT change logical_signal_id. It updates the fingerprint and produces a
  new SignalRevision (same logical_signal_id, new revision_number, new
  fingerprint, same previous_revision_id chain).
- Provider symbol mappings (Instrument) are separate from identity; identity
  links to provider reference, not instrument mapping.

F. Key invariants (authoritative):
- logical_signal_id is immutable; never changes across revisions; never derived
  from mutable canonical content. Derivation is from provider/stable reference only.
- Changing canonical content updates fingerprint and produces a new SignalRevision
  with the same logical_signal_id; revision_number increments; previous_revision_id
  links to prior revision; no branching.
- Deduplication compares logical_signal_id + fingerprint, not full object equality.
- Same logical_signal_id + same fingerprint = duplicate (no new revision).
- Same logical_signal_id + different fingerprint = new revision.
- Different logical_signal_id = different logical signal (regardless of fingerprint).

## 12. Signal Event Model

SignalEvent fields (complete reference):
- event_id: UUID (audit-only, non-deterministic).
- signal_identity: SignalIdentity (reference, not embedded Signal).
- event_type: EventType enum.
- timestamp_utc: datetime (logical event ordering; ingestion timestamp
  may differ, handled by SourceIdentity/provenance).
- previous_revision_id: Optional[UUID] (revision before event; None for
  CREATED if no prior revision).
- new_revision_id: Optional[UUID] (revision produced; None for events
  that don't produce revisions, e.g., CANCELLED might link to existing
  revision).
- event_payload: Optional[dict[str, Any]] (structured event-specific
  details; core does not enforce schema; adapter/populates as needed).
- provenance: ProviderSource (optional; ingestion provenance at event
  time; allows tracking provider changes over signal lifecycle).

Event sequence rules (proposed invariants, not enforced):
- CREATED must be first for a signal_identity.
- CANCELLED can occur after ACTIVE; once CANCELLED, no ACTIVE/EXECUTING
  events allowed (ARCHIVED allowed as terminal).
- REVISED requires previous ACTIVE; produces new revision.
  (Historical note: the early draft said "REVISED requires previous ACTIVE
  or MODIFIED" — that wording is superseded. The MODIFIED event type was
  removed and REVISED now covers all revision-producing changes; see
  Section 3.10, Section 14, and the final paragraph of Section 31.)
- EXECUTING requires ACTIVE; EXECUTED requires EXECUTING.
- INCOMPLETE_SIGNAL_RECEIVED allowed only in DRAFT or ACTIVE; does not
  transition state alone.

## 13. Signal Revision Model

> **STATUS: HISTORICAL / SUPERSEDED — NOT AUTHORITATIVE**
>
> The authoritative SignalRevision definition is Section 3.12 of this
> document. Section 13 retains an earlier draft that used the field names
> `snapshot_reference` and `key_snapshot_fields`. Those field names have
> been removed from the canonical model; the authoritative fields are
> `canonical_snapshot` (a frozen mapping of `(str, object)` pairs
> containing the full semantic state of the Signal at revision time) and
> `event_reference_id` (a reference to the producing SignalEvent by ID).
> This section is preserved only for the audit trail of how the model
> evolved. Do not implement against Section 13.

SignalRevision fields (deeply immutable, no embedded recursive objects):

> The list below is HISTORICAL and DOES NOT MATCH the implementation.
> See Section 3.12 for the authoritative field list.

- revision_id: UUID.
- signal_identity: SignalIdentity (shared across revisions; same logical
  signal identity).
- previous_revision_id: Optional[UUID]; None only for first revision.
- snapshot_reference: Optional[UUID] (optional reference to persistent
  snapshot store; Phase 1 reserves this; not an embedded Signal object).
  [Historical field name; replaced by `canonical_snapshot` in §3.12.]
- key_snapshot_fields: frozen_mapping_type (optional frozen mapping of
  audit-relevant fields at revision time; never embeds a full Signal).
  [Historical field name; replaced by `canonical_snapshot` in §3.12.]
- event_reference_id: Optional[UUID] (reference to SignalEvent by event_id;
  not embedded SignalEvent).
- created_at_utc: datetime.

Chain properties:
- Revisions form a singly-linked list via previous_revision_id; no
  branching; no gaps.
- Replay/reconstruction: traverse revisions by ID references; apply
  `canonical_snapshot` (the authoritative field; historical name was
  `key_snapshot_fields`) and event payload for full audit; no recursive
  Signal embedding.
- Deduplication compares SignalIdentity (logical signal) + fingerprint
  (canonical content); revisions themselves are not compared for identity.

## 14. Signal Lifecycle / State Model

States (LifecycleState):
DRAFT -> ACTIVE -> CANCELLED / EXPIRED -> ARCHIVED

Transitions:
- DRAFT: initial; partial or ambiguous allowed.
- ACTIVE: complete or actionable partial signal.
- CANCELLED: explicit cancellation; terminal except ARCHIVED.
- EXPIRED: signal validity/timeout reached (optional terminal before ARCHIVED).
- ARCHIVED: final audit state; no further events except audit logs.

Note: CANCELLED and EXPIRED are terminal except for ARCHIVED; no transition
back to ACTIVE. EXECUTING and EXECUTED are not signal lifecycle states; they
are execution events tracked by downstream ExecutionIntent / Order /
ExecutionResult / Position models.

Note: MODIFIED and REVISED are event types (SignalEvent), not persistent
lifecycle states. A modification event produces a new SignalRevision but
does not transition lifecycle_state out of ACTIVE (or DRAFT for partial).
This keeps the lifecycle machine minimal and deterministic.

Event classification (signal change vs execution activity):
- Signal-change events (affect SignalRevision): CREATED, REVISED, CANCELLED,
  INCOMPLETE_SIGNAL_RECEIVED.
- Execution-related events (downstream; do not change Signal core state
  directly, but may reference it): EXECUTING, EXECUTED, PARTIAL_CLOSE,
  CLOSE_COMPLETE, SCALE_IN, SCALE_OUT, REVERSAL.
- Modification events (produce new revision): SL_MOVED, TP_MOVED,
  BREAKEVEN, SCALE_IN.
- Signal lifecycle events (state transitions): CREATED (DRAFT/ACTIVE),
  CANCELLED (CANCELLED), ARCHIVED (ARCHIVED).
- Execution events (downstream only): EXECUTING, EXECUTED; these represent
  ExecutionIntent/Order/Position activity, not Signal domain state changes.

Execution boundary clarification:
- Signal Core ends at Signal + SignalEvent + SignalRevision + abstract
  ExecutionIntent/Order/Position interfaces.
- ExecutionResult (new abstract concept) represents the outcome of
  execution (filled, rejected, partial fill, error) and links to
  ExecutionIntent or Order, not directly to Signal. It is deferred to
  future phases but defined here for boundary clarity.
- ExecutionResult fields (interface only): result_id, intent_reference,
  result_type (FILLED, REJECTED, PARTIAL, ERROR), timestamp, message.
- ExecutionResult does not modify Signal; it produces audit events (e.g.,
  EXECUTED event referencing signal identity) through adapter/execution layer.

## 15. Explicit Distinction Between Concepts

Signal: The canonical description of a trading idea (direction, entry, SL,
TP, status, identity). Independent of ingestion, broker, execution.

SignalEvent: Lifecycle event (created, modified, cancelled). Immutable
log entry; does not contain full Signal but references it.

SignalRevision: Immutable snapshot of Signal at a point in time. Contains
full Signal state; linked to previous revision; enables replay.

ExecutionIntent: Bridge from Signal to execution engine. Defines what
actions to attempt (submit, modify, cancel). Not implemented in Phase 1;
interface defined.

Order: Downstream abstract contract representing an execution request.
Contains direction, price levels, quantities, status. No broker-specific
logic in core.

Position: Downstream abstract contract representing open exposure.
Contains direction, open quantity, current SL/TP, status. Links optionally
to SignalIdentity for audit/replay.

These must never be combined: a Signal is not an Order; a SignalEvent
is not a SignalRevision; ExecutionIntent derives from Signal but is not
the same object.

### 15.5 SignalInstruction / SignalAction (Canonical Semantic Concept)

Purpose: A proper canonical domain concept — not an adapter convenience,
not a broker Order — representing instructions that manage a signal.
The canonical domain recognizes two entry forms from ingestion:
- A canonical Signal (describes the trading idea at a point in time).
- A canonical SignalInstruction (describes an action directed at an existing
  signal, derived from a provider message that is not a new signal).

Pipeline (authoritative):
Provider message → parser → canonical Signal OR canonical SignalInstruction
→ SignalInstruction → state transition / revision (where applicable) → ExecutionIntent (later phase)

SignalInstruction must represent all of the following without becoming a broker Order:
- OPEN: initiate/open a new signal.
- MODIFY: general modification of existing signal (produces new SignalRevision).
- CANCEL: cancel an existing signal (lifecycle transition to CANCELLED).
- CLOSE: close / terminate the signal.
- PARTIAL_CLOSE: close part of the exposure (execution-level; may link to existing signal identity).
- MOVE_SL: move stop-loss to a new price.
- MOVE_TP: move take-profit target(s) to new price(s).
- BREAKEVEN: adjust SL to entry price.
- TRAIL: trailing stop update (semantic instruction; execution handles mechanics).
- SCALE_IN: expand/add to entry levels (multiple levels preserved exactly; strategy determines scale-in/averaging semantics later).
- SCALE_OUT: reduce exposure (execution-level; does not change signal entry levels unless revision produced).
- REVERSE: reverse direction (produces new direction; handled via event/revision).

Properties:
- SignalInstruction is separate from Signal, SignalEvent, ExecutionIntent, and Order.
- It does not embed a full Signal; it references SignalIdentity.
- It specifies the action type and parameters (e.g., new SL price for MOVE_SL,
  new direction for REVERSE, new TP tuple for MOVE_TP).
- It is not a broker order; it carries no broker-specific fields (broker_reference,
  order_type, lot size, execution conditions). Those belong to ExecutionIntent / Order.
- The adapter/parser converts provider syntax ("move SL to BE", "add TP",
  "close half") into SignalInstruction; the core treats it as a canonical
  semantic instruction that produces a SignalEvent and, when content changes,
  a new SignalRevision.
- Where the instruction changes canonical content (e.g., MOVE_SL changes SL price),
  a new SignalRevision is produced; where it does not change content (e.g., some
  CLOSE instructions), it may only produce a SignalEvent.

Where actions belong:
- SignalInstruction: adapter/conversion layer produces from provider syntax; core
  stores/references as a canonical semantic instruction.
- SignalEvent: records that an instruction occurred (SL_MOVED, TP_MOVED, BREAKEVEN,
  SCALE_IN, SCALE_OUT, REVERSAL, CANCELLED, etc.).
- SignalRevision: captures the new canonical state produced by applying the instruction.
- ExecutionIntent: translates Signal + SignalInstruction + current state into concrete
  execution plans (submit/cancel/modify orders) — deferred to future phases.
- Order: concrete broker/execution request produced by ExecutionIntent.
- ExecutionResult: outcome of Order execution; separate from Signal lifecycle.

## 16. Partial / Incomplete Signal Representation

Partial signals use SignalStatus.PARTIAL with optional fields set to None:
- Missing TP: take_profit_targets = [] or None (explicit absence, not
  invented default).
- Missing SL: stop_loss = None.
- Missing entry price for market: entry_price = None; entry_type = MARKET.
- Multi-message construction: initial message produces DRAFT/PARTIAL Signal;
  subsequent messages produce MODIFIED/REVISED events with updated fields;
  final state may become ACTIVE/COMPLETE when all fields present.
- Parser must never invent TP or SL values; must never set entry_type
  to SINGLE when syntax indicates RANGE but syntax is unclear.

Ambiguous signals: SignalStatus.AMBIGUOUS; parser must explicitly set this
when syntax is unclear (e.g., conflicting entry descriptions, missing
direction indicators). No silent default.

## 17. Ambiguous Signal Representation

Ambiguity is represented explicitly, not as a hidden state:
- SignalStatus = AMBIGUOUS.
- LifecycleState = DRAFT (not promoted to ACTIVE).
- Fields may be partially present (e.g., direction known, entry unknown).
- Event payload may include ambiguity notes (optional event_payload field).
- Parser does not attempt to resolve ambiguity by defaulting to MARKET,
  SINGLE, or any other value.
- Downstream ExecutionIntent is not produced from AMBIGUOUS signals
  (reserved invariant, not enforced in Phase 1).

### 10.5 Unknown vs Absent vs Ambiguous Semantics (Explicit)

For any field (entry_price, stop_loss, take_profit_targets, entry_geometry,
entry_range, entry_levels):

- Absent (explicit absence):
  - Containing field is None (e.g., stop_loss: Optional[Price] = None).
  - Indicates the provider explicitly did not provide this value, or it is
    not applicable to this signal.
  - Different from missing: absence is a meaningful state.
- Unknown (value unknown but field present in representation):
  - For geometry: entry_geometry could be unknown only via SignalStatus.AMBIGUOUS
    (parser could not determine); no separate "unknown geometry" enum member.
  - For price fields: None at containing level (same as absent), but if
    the field is expected and missing unexpectedly, the parser should mark
    the signal AMBIGUOUS rather than silently assume absence.
- Explicit zero:
  - Price(value=Decimal("0.0")) is a valid price; zero is meaningful
    (e.g., breakeven SL, zero-price instrument).
- Ambiguous (syntax unclear):
  - SignalStatus = AMBIGUOUS.
  - LifecycleState remains DRAFT.
  - Parser must not resolve ambiguity by selecting default values (e.g.,
    defaulting to MARKET, SINGLE, or any price value).
  - Ambiguity is a state of the entire signal, not a property of individual
    fields; individual fields may be partially present without making the
    signal ambiguous.
- Partial (multi-message construction in progress):
  - SignalStatus = PARTIAL.
  - Some fields intentionally missing (e.g., TP not yet received); these
    are absent by design, not ambiguous.
  - Parser does not invent missing fields to complete the signal.

Distinction preserved in domain:
- Absent: None at container.
- Unknown (for geometry): only via AMBIGUOUS status; no "unknown" enum.
- Zero: Price(value=Decimal("0.0")) as a real value.
- Ambiguous: SignalStatus.AMBIGUOUS + DRAFT state.

## 18. Modification Semantics

Modifications produce new SignalRevision + SignalEvent (REVISED or MODIFIED):

- SL movement (SL_MOVED): new SignalRevision updates stop_loss; event
  references previous and new revision.
- TP movement (TP_MOVED): updates take_profit_targets; event payload may
  include previous targets and new targets.
- Breakeven (BREAKEVEN): SL moved to entry price; event records previous
  SL and new SL = entry price.
- Partial close (PARTIAL_CLOSE): does not modify Signal directly but
  produces SignalEvent; Signal status may remain ACTIVE; ExecutionIntent
  handles partial quantity closure.
- Reversal (REVERSAL): event type REVERSAL; new direction established; previous
  open direction is effectively cancelled/reversed (handled at ExecutionIntent
  level, not by mutating Signal).
- Scale-in (SCALE_IN): event type SCALE_IN; entry_levels may expand; revision
  updates Signal snapshot.

Modification rules (proposed invariants):
- A SignalRevision must reference previous revision (no branching).
- Event payload should contain previous state references for audit.
- Signal identity remains unchanged; fingerprint updates if canonical
  content changes.

## 19. Multi-Message Signal Reconstruction Requirements

Requirements:
- Multi-message signals use the same SignalIdentity (provider_reference +
  canonical content normalization).
- First message: creates Signal (DRAFT or ACTIVE) with PARTIAL status.
- Subsequent messages: produce SignalEvent (INCOMPLETE_SIGNAL_RECEIVED or
  REVISED) linking to same identity.
- Final message: produces SignalEvent (REVISED or MODIFIED) that completes
  fields; SignalStatus transitions to COMPLETE; lifecycle_state may
  transition to ACTIVE (if previously DRAFT) or remain ACTIVE.
- Parser must distinguish between:
  - New message for new signal (different identity).
  - Revision message (same identity, different content -> new revision).
  - Duplicate message (same identity, same fingerprint -> no new revision,
    potentially duplicate event, handled by ingestion layer).
- Event sequence must be preserved in ingestion order (logical order) even
  if ingestion timestamps differ.

## 20. Validation Invariants

Invariants (defined, not implemented in Phase 1):

Geometry (direction-based):
- BUY: SL.value < entry_price.value (when both present). If SL is at or
  above entry, invalid geometry.
- BUY: TP targets >= entry_price.value; targets strictly ordered
  ascending; no duplicates.
- SELL: SL.value > entry_price.value (when both present).
- SELL: TP targets <= entry_price.value; targets strictly ordered
  descending; no duplicates.

Range:
- RANGE: low <= high when both present.
- RANGE: SL must not fall inside range (for simple cases; complex range
  strategies deferred).
- MULTIPLE: entry_levels ordered; no empty list when entry_type = MULTIPLE.

Lifecycle:
- DRAFT: initial state; allowed for partial and ambiguous.
- CANCELLED after ARCHIVED is invalid; ARCHIVED after CANCELLED is valid terminal sequence.
- No transition from CANCELLED or EXPIRED back to ACTIVE.
- REVISED event requires previous revision reference (no branching).
- SignalRevision chain must be contiguous (no gaps).

Completeness/Ambiguity:
- PARTIAL and AMBIGUOUS are valid states; parser must not auto-promote.
- COMPLETE requires all fields appropriate to entry_type present (e.g.,
  SINGLE requires entry_price; RANGE requires entry_range; MULTIPLE requires
  non-empty entry_levels).

Identity:
- logical_signal_id is completely independent of mutable canonical content; it is derived from provider reference / stable ingestion reference, not from content fingerprint.
- fingerprint is derived from canonical content (normalized Signal fields) and changes when content changes; identity remains unchanged across revisions.
- Same logical_signal_id + same fingerprint = duplicate; same logical_signal_id + different fingerprint = new revision (new SignalRevision, same identity).
- A revision must never change logical_signal_id.

Conflict:
- Conflicting instructions (e.g., SL moved below TP for BUY) are defined
  as invalid; validator must detect them; parser should not silently
  resolve conflicts.

## 21. Validation Errors vs Warnings

Phase 1 defines categories but does not implement validator framework:

Errors (must prevent invalid Signal creation/revision):
- Direction/geometry conflict (BUY with SL >= entry).
- Range invalid (low > high).
- Multiple levels empty when MULTIPLE.
- Lifecycle transition invalid (e.g., transition from CANCELLED/EXPIRED back to ACTIVE).
- Revision chain gap (missing previous_revision reference when expected).
- Identity derivation failure (fingerprint mismatch with identity).

Warnings (may be logged/reported but do not prevent creation; downstream
systems decide):
- Ambiguous entry syntax (parser should set AMBIGUOUS rather than invent).
- Missing TP (allowed; not an error unless strategy requires TP).
- Partial signal (allowed; multi-message construction in progress).
- Unknown entry price (allowed for MARKET; warning if SINGLE expected).

Distinction reason: Errors enforce structural integrity; warnings allow
flexibility for multi-message construction and partial signals without
blocking ingestion.

## 22. Serialization / Deserialization Strategy

Proposed strategy (not implemented):

- Domain objects use frozen Python dataclasses (standard library).
- Serialization uses a manual or framework-assisted approach that converts:
  - Decimal -> string (to preserve precision; never float).
  - UUID -> string.
  - datetime -> ISO 8601 string (UTC).
  - Optional fields -> present with null value or omitted based on schema.
- Deserialization validates types and reconstructs frozen objects; any
  mutation attempt raises exception.
- Provider-specific syntax is never serialized inside Signal; adapter layer
  handles conversion to/from ProviderSource/provenance fields.
- Fingerprint is serialized as a string; identity derived on load; duplicate
  detection uses identity + fingerprint comparison before creating new Signal.

Performance: Serialization overhead is deferred to replay/backtesting and
analytics phases, not the hot path. Hot path uses frozen objects directly.

## 23. Equality and Hashing Semantics

Strategy:
- Frozen dataclass provides default __eq__ and __hash__ based on all fields.
- For Signal: equality includes identity, direction, entry, SL, TP,
  status, lifecycle_state. Two Signals with same fields are equal (same snapshot).
- For SignalIdentity: equality includes logical_signal_id, provider_identity.
  Same identity = same logical signal.
- Deduplication uses fingerprint (not full object equality) to handle
  minor differences (e.g., revision references) that don't define canonical
  content.
- Hashing: frozen objects hash based on contents. This supports use in sets
  and dictionaries (e.g., dedup collections) but does not replace fingerprint
  comparison for identity logic.

Immutability requirement: frozen=True ensures hash stability; mutable
objects must not be embedded (lists must be frozen tuples or converted to
immutable representations).

## 24. Immutability Strategy

Strategy: Frozen Python dataclasses (frozen=True) for all domain objects.

Details:
- Signal, SignalEvent, SignalRevision, ProviderSource, SourceIdentity,
  Price, PriceRange are frozen.
- Nested collections (e.g., take_profit_targets) must be tuples (not
  lists) or converted to frozen representations on creation.
- Any "modification" creates a new instance with updated fields; original
  instance remains unchanged.
- Revision chain links via previous_revision_id (reference), not mutation.
- Event log is append-only; no event can be deleted or modified.
- ExecutionIntent, Order, Position interfaces do not require immutability in
  Phase 1, but downstream implementations should respect audit requirements.

Performance impact: Frozen objects have slightly higher creation cost than
mutable objects (copy-on-create), but benefit from hash stability and
deterministic behavior required for replay and audit.

## 25. Provider-Specific Metadata (Excluded from Canonical Signal)

Strategy:
- Provider-specific metadata (message IDs, chat references, formatting notes,
  adapter syntax details) does NOT belong in the canonical Signal.
- Such metadata belongs to the adapter/provenance/source layer (ProviderSource,
  SourceIdentity, future adapter interface), not the core domain object.
- This keeps Signal focused on semantic trading information, makes fingerprinting
  deterministic (no mutable adapter fields), and prevents adapter pollution.
- Adapter interface (future phase) defines conversion rules; core defines
  only the canonical signal contract.

## 12.5 Hot Path Analysis (Performance Design)

The hot path is the live signal processing path where Signals are created,
revised, and audited. It must be low-latency and low-allocation.

Allocation count (per Signal creation):
- Signal object: 1 frozen dataclass instance.
- Nested frozen tuples: 1 for take_profit_targets, 1 for entry_levels (only
  if MULTIPLE). No list allocations.
- Price objects: 1 per price value present (entry, SL, each TP, each entry
  level). Minimal.
- SignalIdentity: 1 value object.
- SignalRevision: 1 frozen instance per revision event (not per signal
  processing unless revision occurs).
- SignalEvent: 1 frozen instance per lifecycle event.

Nested object count (maximum depth):
- Signal -> SignalIdentity (value object, depth 1).
- Signal -> Price (value object, depth 2 for price fields).
- SignalRevision does NOT embed full Signal (no depth recursion); uses ID
  references and frozen snapshot fields only.
- SignalEvent references SignalIdentity by UUID (no embedded Signal).

Hashing and equality:
- Frozen dataclass provides default __hash__ based on all fields.
- Hash stability requires nested frozen objects (tuples, frozen mappings, not
  lists/dicts). All nested collections converted to frozen representations.
- Deduplication uses fingerprint (str) comparison, not full object hash.
  This avoids hashing large nested structures for identity checks.

Decimal usage:
- All monetary values use Python Decimal; float is banned.
- Decimal creation overhead is acceptable for domain objects; no arithmetic
  is performed in the hot path (invariants deferred to pure functions, not
  class constructors).

Deep immutability:
- All nested collections are frozen tuples or frozen mappings; no mutable
  list/set/dict embedded in domain objects.
- event_payload uses frozen mapping, not dict.
- Any external mutable state must be copied into frozen structures before
  embedding.

Metadata overhead:
- ProviderSource, SourceIdentity, Instrument add minimal overhead (small
  frozen value objects) but prevent adapter pollution and enable identity
  tracking without external lookups.
- Fingerprint (str) is computed at creation time; stored once per signal/revision.
  Deduplication compares fingerprints directly (fast string comparison).

Copying overhead:
- Frozen objects create copies only when new instances are produced (e.g.,
  new revision). Hot path processing does not require copying unless a
  modification event occurs.
- Serialization overhead deferred to replay/analytics; not in hot path.

Serialization boundaries:
- Serialization framework deferred; hot path uses frozen objects directly.
- When serialization is needed (replay/analytics), Decimal serialized as
  string, UUID as string, frozen tuples converted to arrays manually.

Unnecessary work removed:
- No embedded recursive objects (Signal -> SignalRevision -> Signal removed).
- No mutable collections requiring defensive copying.
- No validation framework overhead in hot path (invariants are pure
  functions, not class-level validators called during creation).
- No framework initialization overhead (standard library only).

## 26. Implementation Approach Comparison

### A. Python Frozen Dataclasses (Standard Library)
- Performance: Very fast initialization; minimal overhead; suitable for
  high-frequency hot path.
- Memory: Low overhead; no extra framework objects.
- Validation: Manual (pure functions); no built-in declarative framework.
  This aligns with principle: correctness before optimization; validation
  invariants are defined separately from object creation.
- Typing: Excellent Python 3.13 + mypy integration; frozen ensures
  immutability at type-check time.
- Serialization: Requires manual __dict__ conversion or library helper;
  no framework dependency required in Phase 1.
- Immutability: frozen=True; nested frozen objects enforce audit chain.
- Developer ergonomics: Very high; standard library; no new dependencies.
- Hot path suitability: Excellent. Low initialization cost; no validation
  overhead in hot path (validation deferred to pure functions, not class
  constructors).

### B. Pydantic v2 (BaseModel, frozen/config)
- Performance: Faster validation than v1, but higher initialization
  overhead than plain dataclass; serialization overhead present even when
  not needed.
- Memory: Slightly higher due to internal validation caches and schema
  storage.
- Validation: Built-in declarative framework; excellent for complex
  invariants, but introduces dependency.
- Typing: Excellent; integrates with mypy.
- Serialization: Excellent (JSON/dict); introduces pydantic-core dependency.
- Immutability: frozen=True available; nested frozen required.
- Developer ergonomics: High; but dependency contradicts principle #13
  (no dependencies without justification) in Phase 0/1.
- Hot path suitability: Good but unnecessary overhead; validation framework
  not required if invariants are implemented as pure functions.

### C. attrs (frozen, validators, converters)
- Performance: Very close to dataclass; sometimes faster serialization with
  cattrs.
- Memory: Similar to dataclass; slightly more overhead with validators.
- Validation: Validators/converters built-in; less declarative than Pydantic.
- Typing: Good; requires annotations for best mypy support.
- Serialization: Requires cattrs or manual code; introduces dependency.
- Immutability: frozen=True; excellent.
- Developer ergonomics: Very high; but introduces new dependency (attrs);
  justifiable only if needed.
- Hot path suitability: Excellent; but no significant advantage over
  standard library dataclass for Phase 1 requirements.

### D. Plain Python Classes (Manual __init__, __slots__)
- Performance: Potentially fastest if fully optimized; but high maintenance
  cost for complex domain.
- Memory: Lowest with __slots__; but loses flexibility for nested value
  objects.
- Validation: Fully manual.
- Typing: Requires discipline; easy to miss fields or break immutability.
- Serialization: Fully manual.
- Immutability: Manual enforcement; error-prone (accidental mutation easy).
- Developer ergonomics: Poor for complex domain; not recommended.

### E. NamedTuple / NamedTuple Subclass
- Performance: Very fast; very low memory.
- Memory: Very low.
- Validation: None; fully manual.
- Typing: Good.
- Serialization: Limited; difficult to extend with new fields.
- Immutability: Built-in.
- Developer ergonomics: Poor for evolving domain model; not suitable for
  complex nested objects (Signal with nested revisions and events).

## 27. Recommended Implementation Approach

Recommendation: Python 3.13 frozen dataclasses (standard library) for all
domain objects.

Justification:
- Zero additional dependencies (principle #13/14: no new dependencies
  without justification; no infrastructure before needed).
- Excellent performance for hot path: low initialization overhead,
  minimal memory footprint, no framework overhead.
- Excellent type safety with mypy; frozen=True ensures immutability at
  compile-time (shallow; nested objects must also be frozen).
- Developer ergonomics high; standard library; easy to understand,
  test, and maintain.
- Serialization can be added manually when replay/analytics phases
  require it; avoids premature serialization framework dependency.
- Validation invariants implemented as pure functions (not class-level),
  keeping domain objects lean and avoiding framework lock-in.
- Principle #15 (simple architecture) favors standard library over
  external framework.
- Pydantic or attrs can be adopted in a later phase if validation
  complexity exceeds what pure functions can manage cleanly, but no
  justification exists in Phase 1.

## 28. Example Canonical Representations (10+ Signal Forms)

Note: These are design examples showing structure, not implemented code.

### Example A: BUY MARKET, UNSPECIFIED trigger, SL and TP
- direction: BUY
- entry_geometry: MARKET
- entry_trigger: MARKET (explicit market execution specified)
- entry_price: None
- entry_range: None
- entry_levels: ()
- stop_loss: Price(value=Decimal("100.00"))
- take_profit_targets: (Price(value=Decimal("110.00")),)
- instrument: Instrument(canonical_symbol="EURUSD", asset_class=FOREX)
- status: COMPLETE
- lifecycle_state: ACTIVE

### Example B: BUY LIMIT @ SINGLE price
- direction: BUY
- entry_geometry: SINGLE
- entry_trigger: LIMIT
- entry_price: Price(value=Decimal("1.1000"))
- stop_loss: Price(value=Decimal("1.0950"))
- take_profit_targets: (Price(value=Decimal("1.1100")),)
- status: COMPLETE

### Example C: BUY STOP @ SINGLE price
- direction: BUY
- entry_geometry: SINGLE
- entry_trigger: STOP
- entry_price: Price(value=Decimal("1.1050"))
- stop_loss: Price(value=Decimal("1.0950"))
- take_profit_targets: (Price(value=Decimal("1.1150")),)
- status: COMPLETE

### Example D: SELL LIMIT @ SINGLE price
- direction: SELL
- entry_geometry: SINGLE
- entry_trigger: LIMIT
- entry_price: Price(value=Decimal("1.2050"))
- stop_loss: Price(value=Decimal("1.2100"))
- take_profit_targets: (Price(value=Decimal("1.1950")), Price(value=Decimal("1.1900")))
- status: COMPLETE

### Example E: SELL STOP @ SINGLE price
- direction: SELL
- entry_geometry: SINGLE
- entry_trigger: STOP
- entry_price: Price(value=Decimal("1.2000"))
- stop_loss: Price(value=Decimal("1.2100"))
- take_profit_targets: (Price(value=Decimal("1.1950")),)
- status: COMPLETE

### Example F: BUY RANGE (geometry only, UNSPECIFIED trigger unless specified)
- direction: BUY
- entry_geometry: RANGE
- entry_trigger: UNSPECIFIED (provider did not specify; preserved, not defaulted to MARKET)
- entry_range: PriceRange(low=Price(value=Decimal("150.00")), high=Price(value=Decimal("150.50")))
- stop_loss: Price(value=Decimal("149.50"))
- take_profit_targets: ()
- status: PARTIAL
- lifecycle_state: DRAFT

### Example G: MULTIPLE entry levels (MULTIPLE_LEVELS), UNSPECIFIED trigger
- direction: BUY
- entry_geometry: MULTIPLE
- entry_trigger: UNSPECIFIED
- entry_price: None
- entry_range: None
- entry_levels: (Price(value=Decimal("150.00")), Price(value=Decimal("148.00")), Price(value=Decimal("146.00")))
- stop_loss: Price(value=Decimal("144.00"))
- take_profit_targets: (Price(value=Decimal("160.00")), Price(value=Decimal("170.00")))
- status: COMPLETE
- lifecycle_state: ACTIVE
- Note: Quantity/allocation is deferred to ExecutionIntent/Strategy/Risk.

### Example H: Provider gives direction + price but no order semantics
- direction: BUY
- entry_geometry: SINGLE
- entry_trigger: UNSPECIFIED (preserved; adapter must not default to MARKET)
- entry_price: Price(value=Decimal("3350"))
- stop_loss: None
- take_profit_targets: ()
- status: PARTIAL
- lifecycle_state: DRAFT

### Example I: Partial / multi-message construction
- Message 1 (DRAFT, PARTIAL): BUY, entry_geometry=MARKET, entry_trigger=UNSPECIFIED,
  SL=Price(value=Decimal("100")), TP=(), status=PARTIAL.
- Message 2 (REVISED event): same logical identity; TP updated to
  (Price(value=Decimal("110")),); status=COMPLETE; lifecycle_state=ACTIVE.
- Event sequence: CREATED -> INCOMPLETE_SIGNAL_RECEIVED -> REVISED.

### Example J: SL modification (Breakeven)
- Original revision: stop_loss = Price(value=Decimal("145.00")), entry_price = Price(value=Decimal("150.00"))
- New revision: stop_loss = Price(value=Decimal("150.00")) (breakeven)
- Event: EventType.SL_MOVED or BREAKEVEN
- Identity unchanged; fingerprint changes; new SignalRevision linked to previous.

### Example K: TP modification (add second TP target)
- Original signal: take_profit_targets = (Price(value=Decimal("160.00")),)
- New revision: take_profit_targets = (Price(value=Decimal("160.00")), Price(value=Decimal("170.00")))
- Event: EventType.TP_MOVED or REVISED

### Example L: Partial close instruction (execution concept, separate from signal modification)
- Signal remains ACTIVE; signal content unchanged (same revision possible).
- ExecutionIntent produces partial quantity closure; SignalEvent of type
  PARTIAL_CLOSE links to signal identity; no SignalRevision produced unless
  the partial close is represented as a signal-level event requiring audit.
- Note: Partial close is an execution event; the signal description does not
  change unless strategy/risk rules require an update.

### Example M: Cancellation
- Original signal: ACTIVE, BUY, SINGLE, entry_geometry=SINGLE, entry_trigger=LIMIT,
  entry_price=Price(value=Decimal("150")), SL=Price(value=Decimal("145")), identity preserved.
- Event: CANCELLED.
- Lifecycle: CANCELLED; no EXECUTING or EXECUTED allowed after (signal-level);
  execution events cease through adapter/execution layer.
- Signal identity preserved; new SignalRevision may reference CANCELLED event via event_reference_id.

## 29. Edge Cases to Support Later

- Multi-instrument signals: a single Signal describing exposure across
  multiple instruments; deferred to future architecture.
- Cross-account or multi-user signals: user/account identity is out of
  scope for core domain (adapter/execution layer handles).
- Strategy-linked signals: linking Signal to strategy configuration (e.g.,
  risk parameters) deferred; core remains independent of strategy config.
- Dynamic quantity allocation per TP level: reserved but deferred (current
  domain defines targets, not allocations).
- Time-based conditions (time stops, session limits): deferred to strategy
  or execution layer.
- Partial/incomplete signals with conflicting syntax: parser must set
  AMBIGUOUS rather than resolve; core supports AMBIGUOUS state.
- Reversal identity policy: whether reversal creates new identity or updates
  existing identity deferred; REVERSAL event defined, identity policy not
  enforced.
- Complex entry instructions (e.g., conditional orders): deferred to
  ExecutionIntent interface.

## 30. Deferred to Later Phases

- Parser and adapter implementation (provider syntax conversion).
- Telegram/Discord/API ingestion adapters.
- Broker adapter interface implementation.
- ExecutionIntent concrete implementation and order submission logic.
- Order and Position concrete implementations.
- Strategy engine (user-specific strategies, risk parameters).
- Risk engine (lot sizing, exposure, max drawdown controls).
- Replay and backtesting system (uses revision chain but not implemented).
- Analytics and reporting (uses event log and revisions; framework deferred).
- Database persistence (revision chain storage, event storage, audit database).
- Redis or other external state storage.
- AI inference (explicitly excluded from live path per AGENTS.md).
- Serialization framework (manual conversion proposed; framework deferred).
- Full validation framework (pure functions proposed; framework deferred).
- Multi-instrument, multi-account, or cross-provider signal aggregation.

## 31. Phase 1 Implementation Sequence

Sequence (no code implemented in this document; steps for builder action):

1. Create packages/signal_core/enums.py — define TradeDirection, EntryType,
   LifecycleState, EventType, SignalStatus, SourceType.
2. Create packages/signal_core/value_objects.py — frozen dataclasses for
   ProviderSource, SourceIdentity, Price, PriceRange.
3. Create packages/signal_core/domain.py — frozen dataclasses for Signal,
   SignalIdentity, SignalRevision, SignalEvent.
4. Create packages/signal_core/interfaces.py — abstract interfaces/contracts
   for ExecutionIntent, Order, Position (no concrete implementation).
5. Create packages/signal_core/invariants.py — pure functions defining
   validation rules (geometry, lifecycle, identity). Not class-level
   validators.
6. Create tests/unit/test_domain_immuntability.py — verify frozen behavior,
   hash stability, identity derivation.
7. Create tests/unit/test_invariants.py — verify pure function invariants
   for basic geometry and lifecycle rules.
8. Verify ruff clean; verify mypy clean; verify pytest passes; verify no
   new dependencies added to pyproject.toml.
9. Update docs/phase-1-signal-core-design.md if implementation reveals
   design adjustments (but architecture decisions remain unchanged).
10. Document adapter interface requirements (provider syntax conversion,
    ingestion provenance) but do not implement adapter.

Constraints during implementation:
- No Telegram/Discord/broker/DB/AI/user/strategy/risk/execution/analytics
  code.
- No new dependencies.
- Partial/incomplete signals preserved explicitly (SignalStatus PARTIAL,
  AMBIGUOUS; None for unknown, not zero for missing).
- Deterministic identity preserved; fingerprint derived from normalized
  content.
- Every production change followed by ruff, mypy, pytest, diff inspection.
- Every production bug receives regression test (enforced by REVIEWER role).

## Phase 1 Design Implementation Readiness

Approved design decisions (Builder may implement):
- Frozen dataclass standard library approach for Signal, SignalEvent,
  SignalRevision, Instrument, ProviderSource, SourceIdentity, Price,
  PriceRange, and value objects.
- SignalIdentity with stable logical_signal_id, provider_identity,
  source_identity (revision_sequence belongs to SignalRevision, not identity).
- EntryGeometry (MARKET, SINGLE, RANGE, MULTIPLE) + EntryTrigger (MARKET,
  LIMIT, STOP, UNSPECIFIED) as separate enums.
- Instrument value object (canonical_symbol, asset_class) without provider
  symbol mapping pollution.
- Deep immutability: frozen tuples for collections; frozen mappings for
  metadata; no embedded recursive objects (SignalRevision does not embed
  Signal; SignalEvent does not embed Signal).
- Lifecycle minimal machine: DRAFT, ACTIVE, CANCELLED, EXPIRED, ARCHIVED
  (no persistent MODIFIED/REVISED states; EXECUTING and EXECUTED removed
  and belong to downstream execution events).
- Event categories separated: lifecycle events, modification events,
  execution events.
- Price representation: Price(value=Decimal) required; None at container
  level for unknown/absent; zero = Decimal("0.0"); ambiguous = SignalStatus.AMBIGUOUS.
- Information preservation principle: UNSPECIFIED preserved; no defaulting
  to MARKET; parser must not invent information.
- SignalInstruction / SignalAction concept defined (OPEN, MODIFY, CANCEL,
  CLOSE, PARTIAL_CLOSE, MOVE_SL, MOVE_TP, BREAKEVEN, SCALE_IN, SCALE_OUT,
  REVERSE); belongs to adapter/conversion layer, not broker-specific code.
- Multi-level entries (MULTIPLE_LEVELS): quantity/allocation deferred to
  ExecutionIntent, Strategy, Risk; Signal preserves only entry level prices;
  strategy/execution determines scale-in, staggered entry, averaging, etc.
- Partial/incomplete signals: SignalStatus PARTIAL/AMBIGUOUS; no silent
  promotion to COMPLETE.
- Validation invariants defined as pure functions; no class-level validators.
- Abstract interfaces only for ExecutionIntent, Order, Position,
  ExecutionResult.

Remaining deferred decisions (Builder must NOT implement in Phase 1):
- Parser and adapter implementation (provider syntax conversion, Telegram,
  Discord, manual ingestion).
- Broker adapter interface implementation; broker-specific logic.
- Strategy engine (user-specific strategies, risk parameters).
- Risk engine (lot sizing, exposure, max drawdown, quantity allocation).
- Execution engine logic; concrete ExecutionIntent, Order, Position,
  ExecutionResult implementations.
- Replay and backtesting framework (revision replay logic deferred to later
  phase; chain structure defined only).
- Database persistence; Redis; analytics framework; serialization framework
  (manual conversion strategy defined but framework not implemented).
- Multi-instrument signals; cross-account/user aggregation; provider symbol
  mapping resolution layer.
- AI inference (explicitly excluded from any path).

Explicit statement of what Builder must NOT implement in Phase 1:
- No Python parser code; no Telegram/Discord/API ingestion adapters.
- No broker adapter; no MT4/MT5/cTrader/DXTrade/TradeLocker integration.
- No database code; no Redis; no analytics engine; no replay engine.
- No AI/ML inference; no user account logic; no strategy configuration logic.
- No risk calculations; no lot sizing; no execution order submission logic.
- No serialization framework dependency; no new dependencies added to
  pyproject.toml.
- No mutable collections embedded in domain objects; no recursive domain
  references (SignalRevision must not embed full Signal snapshot).
- No defaulting of UNSPECIFIED to MARKET; no invention of missing fields;
  no silent promotion of PARTIAL or AMBIGUOUS signals.

Explicit statement of what Builder MAY implement in Phase 1:
- All frozen dataclass value objects and enums listed in design.
- Pure invariant functions (not class-level validators).
- Unit tests verifying immutability, identity derivation, fingerprint logic,
  basic invariant behavior, and example representations.
- Skeleton CI verification (ruff/mypy/pytest) with no new dependencies.

Phase 1 Design: READY FOR IMPLEMENTATION

All contradictions resolved:
- LifecycleState: DRAFT, ACTIVE, CANCELLED, EXPIRED, ARCHIVED (EXECUTING and EXECUTED removed; belong to downstream execution events only).
- logical_signal_id: completely independent of mutable canonical content; derived from provider/stable reference; never changes across revisions.
- revision_number: belongs to SignalRevision (starts at 1, increments); removed from SignalIdentity.
- fingerprint: computed from canonical_snapshot (full semantic state) excluding revision metadata; deterministic; same identity + same fingerprint = duplicate; same identity + different fingerprint = new revision.
- EntryGeometry: MARKET, SINGLE, RANGE, MULTIPLE (MULTIPLE_LEVELS terminology; no implicit scale-in assumption).
- EntryTrigger: MARKET, LIMIT, STOP, UNSPECIFIED (separate from geometry; never defaulted to MARKET).
- SignalInstruction: canonical semantic concept with full action set (OPEN, MODIFY, CANCEL, CLOSE, PARTIAL_CLOSE, MOVE_SL, MOVE_TP, BREAKEVEN, TRAIL, SCALE_IN, SCALE_OUT, REVERSE); pipeline defined; not a broker Order.
- SignalRevision snapshot: true non-recursive immutable snapshot (canonical_snapshot frozen mapping + fingerprint + previous_revision_id); independently inspectable without event replay; no embedded Signal; no recursive graphs.
- Provider metadata: removed from Signal; belongs to adapter/provenance layer.
- Deep immutability enforced; standard library frozen dataclasses only; zero new dependencies.
