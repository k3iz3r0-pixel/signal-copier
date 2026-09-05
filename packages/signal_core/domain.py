from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from packages.signal_core.enums import (
    EntryGeometry,
    EntryTrigger,
    EventType,
    InstructionType,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.invariants import (
    validate_ambiguity_lifecycle,
    validate_geometry_entry_consistency,
    validate_price_direction_relationships,
    validate_revision_id_independence,
    validate_revision_sequence,
)
from packages.signal_core.value_objects import (
    Instrument,
    Price,
    PriceRange,
    ProviderSource,
    SourceIdentity,
)

# Canonical snapshot value domain (authoritative from design Section 20 / 3.12).
# float is explicitly excluded per financial-number policy.
# These types MUST be kept in sync between SignalRevision.__post_init__ and canonical_fingerprint().
ALLOWED_SNAPSHOT_TYPES: tuple[type, ...] = (
    str,
    int,
    bool,
    Decimal,
    UUID,
    type(None),
    tuple,
    Price,
    PriceRange,
    Instrument,
    TradeDirection,
    EntryGeometry,
    EntryTrigger,
    LifecycleState,
    SignalStatus,
)


def _normalize_for_fingerprint(obj: object) -> object:
    """Normalize any domain value to a deterministic JSON-serializable primitive.

    Handles all approved domain value types per design Section 20 / 3.14-3.16:
    Decimal -> normalized string; UUID -> string; enums -> value string;
    Price -> tuple of (value_str, currency); PriceRange -> tuple of (low, high);
    Instrument -> tuple of (symbol, asset_class_str); tuple -> normalized tuple.
    """
    if isinstance(obj, Decimal):
        return str(obj.normalize())
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Price):
        return (str(obj.value.normalize()), obj.currency)
    if isinstance(obj, PriceRange):
        return (
            _normalize_for_fingerprint(obj.low) if obj.low is not None else None,
            _normalize_for_fingerprint(obj.high) if obj.high is not None else None,
        )
    if isinstance(obj, Instrument):
        return (
            obj.canonical_symbol,
            obj.asset_class.value
            if hasattr(obj.asset_class, "value")
            else str(obj.asset_class),
        )
    if isinstance(obj, tuple):
        return tuple(_normalize_for_fingerprint(item) for item in obj)
    # Explicit rejection: dict, list, set, and other mutable/unsupported structures
    # are NOT canonical values and must be rejected by the validator, not silently
    # serialized. The normalizer never sees unsupported types.
    # Enum normalization (TradeDirection, EntryGeometry, EntryTrigger, LifecycleState,
    # SignalStatus, EventType, InstructionType, SourceType, AssetClass)
    if isinstance(obj, Enum):
        return obj.value
    # Primitive pass-through
    return obj


def _validate_and_normalize_for_fingerprint(obj: object, path: str = "") -> object:
    """Combined validate-and-normalize pass used exclusively by canonical_fingerprint.

    Authoritative contract (unified with SignalRevision/Event/Instruction):
    type validation reuses _validate_canonical_value (ALLOWED_SNAPSHOT_TYPES).
    Domain value objects (Price, PriceRange, Instrument) are normalized to
    JSON-serializable primitive tuples for deterministic hashing.
    """
    # Authoritative type check: same contract as SignalRevision validator.
    _validate_canonical_value(obj, path)
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, tuple):
        return tuple(
            _validate_and_normalize_for_fingerprint(item, f"{path}[{i}]")
            for i, item in enumerate(obj)
        )
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, Decimal):
        return str(obj.normalize())
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Price):
        return (str(obj.value.normalize()), obj.currency)
    if isinstance(obj, PriceRange):
        return (
            _validate_and_normalize_for_fingerprint(obj.low, f"{path}.low")
            if obj.low is not None
            else None,
            _validate_and_normalize_for_fingerprint(obj.high, f"{path}.high")
            if obj.high is not None
            else None,
        )
    if isinstance(obj, Instrument):
        return (
            obj.canonical_symbol,
            obj.asset_class.value
            if hasattr(obj.asset_class, "value")
            else str(obj.asset_class),
        )
    # ALLOWED_SNAPSHOT_TYPES enum members (TradeDirection, EntryGeometry,
    # EntryTrigger, LifecycleState, SignalStatus) are normalized to their
    # string value for deterministic hashing.
    if isinstance(obj, Enum):
        return obj.value
    # _validate_canonical_value already guaranteed reachability; any
    # other type would have raised. Defensive guard for future enum additions.
    raise TypeError(f"value at '{path}' has unsupported type {type(obj).__name__}")


def canonical_fingerprint(snapshot_tuple: tuple[tuple[str, object], ...]) -> str:
    """Public deterministic SHA-256 fingerprint from normalized canonical snapshot.

    Validates that all snapshot values conform to ALLOWED_SNAPSHOT_TYPES
    (same contract as SignalRevision) before computing fingerprint.
    Rejects duplicate keys in the snapshot tuple (key uniqueness is required
    for unambiguous canonical representation; JSON dict serialization would
    otherwise silently keep only the last value for a repeated key, collapsing
    semantically distinct inputs to the same fingerprint).
    """
    seen_keys: set[str] = set()
    items: list[tuple[str, object]] = []
    for k, v in snapshot_tuple:
        if not isinstance(k, str):
            raise TypeError(f"snapshot key must be str, got {type(k).__name__}")
        if k in seen_keys:
            raise TypeError(
                f"snapshot contains duplicate key '{k}'; "
                f"key uniqueness is required for unambiguous canonical representation"
            )
        seen_keys.add(k)
        items.append(
            (str(k), _validate_and_normalize_for_fingerprint(v, f"snapshot['{k}']"))
        )
    normalized = tuple(sorted(items))
    payload = json.dumps(
        {str(k): v for k, v in normalized},
        separators=(",", ":"),
        ensure_ascii=True,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_canonical_value(obj: object, path: str = "") -> None:
    """Recursively validate that a value conforms to the canonical snapshot value domain.

    Authoritative mechanism shared by SignalRevision, canonical_fingerprint,
    SignalEvent event_payload, and SignalInstruction payload.

    Rejects nested mutable structures (list, dict, set) at any depth.
    Accepts only types in ALLOWED_SNAPSHOT_TYPES.
    Tuple elements are validated recursively.
    """
    if obj is None:
        return
    # Explicit pre-check for mutable collections that must never be accepted
    if isinstance(obj, (list, dict, set)):
        raise TypeError(
            f"value at '{path}' has unsupported mutable type {type(obj).__name__}; "
            f"must be deterministically serializable (str, int, bool, Decimal, UUID, tuple, frozen value objects)"
        )
    if isinstance(obj, ALLOWED_SNAPSHOT_TYPES):
        # For tuples, recursively validate elements (ordering is semantic)
        if isinstance(obj, tuple):
            for i, item in enumerate(obj):
                _validate_canonical_value(item, f"{path}[{i}]")
        return
    # Reject unsupported custom objects or any remaining unsupported types
    raise TypeError(
        f"value at '{path}' has unsupported type {type(obj).__name__}; "
        f"must be deterministically serializable (str, int, bool, Decimal, UUID, tuple, frozen value objects)"
    )


def _validate_deep_immutable_payload(
    payload: tuple[tuple[str, object], ...], payload_name: str
) -> None:
    """Validate a payload tuple has deep immutability (no nested mutable structures)
    and key uniqueness (no duplicate keys).

    Duplicate keys are rejected because key uniqueness is required for unambiguous
    canonical representation; allowing duplicates would silently collapse
    semantically distinct entries during JSON dict serialization.
    """
    if not isinstance(payload, tuple):
        raise TypeError(f"{payload_name} must be a frozen tuple of (str, object) pairs")
    seen_keys: set[str] = set()
    for k, v in payload:
        if not isinstance(k, str):
            raise TypeError(f"{payload_name} key must be str, got {type(k).__name__}")
        if k in seen_keys:
            raise TypeError(
                f"{payload_name} contains duplicate key '{k}'; "
                f"key uniqueness is required for unambiguous canonical representation"
            )
        seen_keys.add(k)
        try:
            _validate_canonical_value(v, f"{payload_name}['{k}']")
        except TypeError as e:
            raise TypeError(f"{payload_name} value for '{k}': {e}")


# Backward-compatible private alias (deprecated; will be removed in future phase)
_canonical_fingerprint = canonical_fingerprint


@dataclass(frozen=True, slots=True)
class SignalIdentity:
    """Stable logical identity for a signal (independent of mutable content)."""

    logical_signal_id: UUID
    provider_identity: ProviderSource
    source_identity: SourceIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.logical_signal_id, UUID):
            raise TypeError("logical_signal_id must be UUID")
        if not isinstance(self.provider_identity, ProviderSource):
            raise TypeError("provider_identity must be ProviderSource")
        if self.source_identity is not None and not isinstance(
            self.source_identity, SourceIdentity
        ):
            raise TypeError("source_identity must be SourceIdentity or None")


@dataclass(frozen=True, slots=True)
class Signal:
    """Canonical immutable trading signal contract."""

    identity: SignalIdentity
    instrument: Instrument
    direction: TradeDirection
    entry_geometry: EntryGeometry
    entry_trigger: EntryTrigger
    created_at_utc: datetime
    entry_price: Price | None = None
    entry_range: PriceRange | None = None
    entry_levels: tuple[Price, ...] = ()
    stop_loss: Price | None = None
    take_profit_targets: tuple[Price, ...] = ()
    status: SignalStatus = SignalStatus.COMPLETE
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    revision_reference_id: UUID | None = None

    def __post_init__(self) -> None:
        # Type validations
        if not isinstance(self.identity, SignalIdentity):
            raise TypeError("identity must be SignalIdentity")
        if not isinstance(self.instrument, Instrument):
            raise TypeError("instrument must be Instrument")
        if not isinstance(self.direction, TradeDirection):
            raise TypeError("direction must be TradeDirection")
        if not isinstance(self.entry_geometry, EntryGeometry):
            raise TypeError("entry_geometry must be EntryGeometry")
        if not isinstance(self.entry_trigger, EntryTrigger):
            raise TypeError("entry_trigger must be EntryTrigger")
        if self.entry_price is not None and not isinstance(self.entry_price, Price):
            raise TypeError("entry_price must be Price or None")
        if self.entry_range is not None and not isinstance(
            self.entry_range, PriceRange
        ):
            raise TypeError("entry_range must be PriceRange or None")
        if not isinstance(self.entry_levels, tuple):
            raise TypeError("entry_levels must be a frozen tuple")
        for item in self.entry_levels:
            if not isinstance(item, Price):
                raise TypeError("entry_levels must contain only Price objects")
        if self.stop_loss is not None and not isinstance(self.stop_loss, Price):
            raise TypeError("stop_loss must be Price or None")
        if not isinstance(self.take_profit_targets, tuple):
            raise TypeError("take_profit_targets must be a frozen tuple")
        for item in self.take_profit_targets:
            if not isinstance(item, Price):
                raise TypeError("take_profit_targets must contain only Price objects")
        if not isinstance(self.status, SignalStatus):
            raise TypeError("status must be SignalStatus")
        if not isinstance(self.lifecycle_state, LifecycleState):
            raise TypeError("lifecycle_state must be LifecycleState")
        if self.revision_reference_id is not None and not isinstance(
            self.revision_reference_id, UUID
        ):
            raise TypeError("revision_reference_id must be UUID or None")
        # created_at_utc must be timezone-aware UTC (design requires immutable timestamp)
        if not isinstance(self.created_at_utc, datetime):
            raise TypeError("created_at_utc must be datetime")
        if self.created_at_utc.tzinfo is None:
            raise ValueError(
                "created_at_utc must be timezone-aware; naive datetime rejected"
            )
        offset = self.created_at_utc.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError(
                "created_at_utc must be UTC-aware (utcoffset == 0); non-UTC aware datetime rejected"
            )

        # Semantic invariants — delegate to pure structural invariant functions (Step 5)
        validate_geometry_entry_consistency(
            self.entry_geometry,
            self.entry_price,
            self.entry_range,
            self.entry_levels,
        )
        validate_price_direction_relationships(
            self.direction,
            self.entry_price,
            self.stop_loss,
            self.take_profit_targets,
        )
        validate_ambiguity_lifecycle(self.status, self.lifecycle_state)


@dataclass(frozen=True, slots=True)
class SignalRevision:
    """Immutable audit snapshot of Signal state at a point in time."""

    revision_id: UUID
    logical_signal_id: UUID
    revision_number: int
    previous_revision_id: UUID | None
    canonical_snapshot: tuple[tuple[str, object], ...]
    fingerprint: str
    created_at_utc: datetime
    event_reference_id: UUID | None = None
    snapshot_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.revision_id, UUID):
            raise TypeError("revision_id must be UUID")
        if not isinstance(self.logical_signal_id, UUID):
            raise TypeError("logical_signal_id must be UUID")
        if not isinstance(self.revision_number, int) or self.revision_number < 1:
            raise ValueError("revision_number must be positive int (>=1)")
        if self.previous_revision_id is not None and not isinstance(
            self.previous_revision_id, UUID
        ):
            raise TypeError("previous_revision_id must be UUID or None")
        if not isinstance(self.canonical_snapshot, tuple):
            raise TypeError("canonical_snapshot must be frozen tuple")
        # Authoritative validation: reuse the same canonical-value mechanism
        # shared by canonical_fingerprint, event_payload, and instruction payload.
        for item in self.canonical_snapshot:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError(
                    "canonical_snapshot must be tuple of (str, object) pairs"
                )
            k, v = item
            if not isinstance(k, str):
                raise TypeError(
                    f"canonical_snapshot key must be str, got {type(k).__name__}"
                )
            _validate_canonical_value(v, f"canonical_snapshot['{k}']")
        # Fingerprint parameter accepted for interface compatibility but is always
        # overwritten with the deterministic SHA-256 derived from canonical_snapshot.
        if not isinstance(self.fingerprint, str):
            raise TypeError(
                "fingerprint parameter must be a string (value is ignored and computed from snapshot)"
            )
        # Structural revision invariants (design Section 20 / 3.12)
        validate_revision_sequence(self.revision_number, self.previous_revision_id)
        validate_revision_id_independence(self.revision_id, self.logical_signal_id)
        # Compute fingerprint deterministically from canonical_snapshot content only
        # (excludes revision metadata: revision_id, logical_signal_id, revision_number,
        # previous_revision_id, event_reference_id, snapshot_version, created_at_utc).
        computed_fingerprint = _canonical_fingerprint(self.canonical_snapshot)
        # Derive fingerprint from snapshot; ignore any caller-supplied value (must be derived, not trusted)
        object.__setattr__(self, "fingerprint", computed_fingerprint)
        if self.event_reference_id is not None and not isinstance(
            self.event_reference_id, UUID
        ):
            raise TypeError("event_reference_id must be UUID or None")
        if not isinstance(self.snapshot_version, int):
            raise TypeError("snapshot_version must be int")
        if not isinstance(self.created_at_utc, datetime):
            raise TypeError("created_at_utc must be datetime")
        if self.created_at_utc.tzinfo is None:
            raise ValueError(
                "created_at_utc must be timezone-aware; naive datetime rejected"
            )
        offset = self.created_at_utc.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("created_at_utc must be UTC-aware (utcoffset == 0)")


@dataclass(frozen=True, slots=True)
class SignalEvent:
    """Immutable audit log entry for signal lifecycle changes."""

    event_id: UUID
    signal_identity: SignalIdentity
    event_type: EventType
    timestamp_utc: datetime
    previous_revision_id: UUID | None = None
    new_revision_id: UUID | None = None
    event_payload: tuple[tuple[str, object], ...] = ()
    provenance: ProviderSource | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, UUID):
            raise TypeError("event_id must be UUID")
        if not isinstance(self.signal_identity, SignalIdentity):
            raise TypeError("signal_identity must be SignalIdentity")
        if not isinstance(self.event_type, EventType):
            raise TypeError("event_type must be EventType")
        if not isinstance(self.timestamp_utc, datetime):
            raise TypeError("timestamp_utc must be datetime")
        if self.timestamp_utc.tzinfo is None:
            raise ValueError(
                "timestamp_utc must be timezone-aware; naive datetime rejected"
            )
        offset = self.timestamp_utc.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("timestamp_utc must be UTC-aware (utcoffset == 0)")
        if self.previous_revision_id is not None and not isinstance(
            self.previous_revision_id, UUID
        ):
            raise TypeError("previous_revision_id must be UUID or None")
        if self.new_revision_id is not None and not isinstance(
            self.new_revision_id, UUID
        ):
            raise TypeError("new_revision_id must be UUID or None")
        if not isinstance(self.event_payload, tuple):
            raise TypeError("event_payload must be frozen tuple of (str, object) pairs")
        if self.event_payload is not None:
            _validate_deep_immutable_payload(self.event_payload, "event_payload")
        if self.provenance is not None and not isinstance(
            self.provenance, ProviderSource
        ):
            raise TypeError("provenance must be ProviderSource or None")


@dataclass(frozen=True, slots=True)
class SignalInstruction:
    """Canonical semantic instruction/action (not a broker Order)."""

    instruction_type: InstructionType
    signal_identity: SignalIdentity
    created_at_utc: datetime
    payload: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.instruction_type, InstructionType):
            raise TypeError("instruction_type must be InstructionType")
        if not isinstance(self.signal_identity, SignalIdentity):
            raise TypeError("signal_identity must be SignalIdentity")
        if self.payload is not None and not isinstance(self.payload, tuple):
            raise TypeError("payload must be a frozen tuple of (str, object) pairs")
        if self.payload is not None:
            _validate_deep_immutable_payload(self.payload, "payload")
        if not isinstance(self.created_at_utc, datetime):
            raise TypeError("created_at_utc must be datetime")
        if self.created_at_utc.tzinfo is None:
            raise ValueError(
                "created_at_utc must be timezone-aware; naive datetime rejected"
            )
        offset = self.created_at_utc.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("created_at_utc must be UTC-aware (utcoffset == 0)")
