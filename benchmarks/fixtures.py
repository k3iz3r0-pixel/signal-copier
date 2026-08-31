"""Deterministic benchmark fixtures for Phase 1 — Step 9.

All fixtures are constructed using the same patterns the production
tests use (see tests/unit/test_signal_domain.py etc.). They are
deterministic: same UUIDs, same timestamps, same decimals across runs.

Fixture set (per Step 9 instruction):
    A. MINIMAL_SIGNAL
    B. NORMAL_SIGNAL
    C. LARGE_SIGNAL
    D. NESTED_SNAPSHOT
    E. MULTI_INSTRUCTION
    F. REVISION_CHAIN

For each fixture the helper also exposes the approximate canonical
snapshot size (number of fields/items) for the fingerprint scaling
analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from packages.signal_core.domain import (
    Signal,
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
)
from packages.signal_core.enums import (
    AssetClass,
    EntryGeometry,
    EntryTrigger,
    EventType,
    InstructionType,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.value_objects import (
    Instrument,
    Price,
    PriceRange,
    ProviderSource,
)

FIXED_TS: datetime = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
FIXED_LOGICAL_ID: UUID = UUID("11111111-1111-4111-8111-111111111111")
FIXED_REVISION_ID_1: UUID = UUID("22222222-2222-4222-8222-222222222222")
FIXED_REVISION_ID_2: UUID = UUID("33333333-3333-4333-8333-333333333333")
FIXED_REVISION_ID_3: UUID = UUID("44444444-4444-4444-8444-444444444444")
FIXED_EVENT_ID: UUID = UUID("55555555-5555-4555-8555-555555555555")
FIXED_PROVIDER_REF: str = "ref-bench-001"


@dataclass(frozen=True)
class FixtureSpec:
    """Documentation of one benchmark fixture."""

    name: str
    description: str
    purpose: str
    canonical_size_fields: int
    canonical_size_total_items: int


FIXTURES: dict[str, FixtureSpec] = {
    "A_MINIMAL_SIGNAL": FixtureSpec(
        name="A_MINIMAL_SIGNAL",
        description=(
            "Smallest valid canonical signal: identity, instrument, "
            "direction, SINGLE geometry, LIMIT trigger, entry price, "
            "no SL, no TP, status COMPLETE, lifecycle ACTIVE."
        ),
        purpose="lower-bound construction cost",
        canonical_size_fields=7,
        canonical_size_total_items=7,
    ),
    "B_NORMAL_SIGNAL": FixtureSpec(
        name="B_NORMAL_SIGNAL",
        description=(
            "Representative signal: identity, instrument, BUY LIMIT, "
            "entry price, SL, multiple TPs, status COMPLETE."
        ),
        purpose="typical-signal construction cost",
        canonical_size_fields=10,
        canonical_size_total_items=12,
    ),
    "C_LARGE_SIGNAL": FixtureSpec(
        name="C_LARGE_SIGNAL",
        description=(
            "Large but valid canonical signal: MULTIPLE geometry with "
            "many entry levels, several TPs, SL present."
        ),
        purpose="upper-bound single-signal construction cost",
        canonical_size_fields=12,
        canonical_size_total_items=24,
    ),
    "D_NESTED_SNAPSHOT": FixtureSpec(
        name="D_NESTED_SNAPSHOT",
        description=(
            "Deep nested immutable canonical snapshot: PriceRange and "
            "tuple of Prices nested inside canonical_snapshot mapping."
        ),
        purpose="canonical_fingerprint cost on nested structures",
        canonical_size_fields=6,
        canonical_size_total_items=20,
    ),
    "E_MULTI_INSTRUCTION": FixtureSpec(
        name="E_MULTI_INSTRUCTION",
        description=(
            "Signal paired with many canonical SignalInstruction "
            "objects covering OPEN/MODIFY/MOVE_SL/MOVE_TP/BREAKEVEN/"
            "SCALE_IN/TRAIL/REVERSE."
        ),
        purpose="SignalInstruction construction cost and instruction fan-out",
        canonical_size_fields=4,
        canonical_size_total_items=4,
    ),
    "F_REVISION_CHAIN": FixtureSpec(
        name="F_REVISION_CHAIN",
        description=(
            "Multiple SignalRevision objects linked through "
            "previous_revision_id using the same logical identity."
        ),
        purpose="revision chain construction cost; chain link integrity",
        canonical_size_fields=5,
        canonical_size_total_items=5,
    ),
}


def _provider_source() -> ProviderSource:
    return ProviderSource(
        provider_name="provider_bench",
        signal_reference=FIXED_PROVIDER_REF,
        ingestion_timestamp_utc=FIXED_TS,
    )


def build_identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=FIXED_LOGICAL_ID,
        provider_identity=_provider_source(),
    )


def _instrument(
    symbol: str = "EURUSD", asset: AssetClass = AssetClass.FOREX
) -> Instrument:
    return Instrument(canonical_symbol=symbol, asset_class=asset)


def _p(value: str) -> Price:
    return Price(value=Decimal(value))


def build_signal(fixture: str) -> Signal:
    """Build a deterministic Signal for the named fixture."""

    identity = build_identity()
    if fixture == "A_MINIMAL_SIGNAL":
        return Signal(
            identity=identity,
            instrument=_instrument("EURUSD", AssetClass.FOREX),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=_p("1.1000"),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=FIXED_TS,
        )
    if fixture == "B_NORMAL_SIGNAL":
        return Signal(
            identity=identity,
            instrument=_instrument("EURUSD", AssetClass.FOREX),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=_p("1.1000"),
            stop_loss=_p("1.0950"),
            take_profit_targets=(
                _p("1.1100"),
                _p("1.1200"),
                _p("1.1300"),
            ),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=FIXED_TS,
        )
    if fixture == "C_LARGE_SIGNAL":
        return Signal(
            identity=identity,
            instrument=_instrument("BTCUSD", AssetClass.CRYPTO),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.MULTIPLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_levels=tuple(_p(str(p)) for p in range(29000, 29012)),
            stop_loss=_p("28800.00"),
            take_profit_targets=tuple(_p(str(p)) for p in (30500, 31000, 31500, 32000)),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=FIXED_TS,
        )
    if fixture == "D_NESTED_SNAPSHOT":
        return Signal(
            identity=identity,
            instrument=_instrument("XAUUSD", AssetClass.COMMODITY),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.RANGE,
            entry_trigger=EntryTrigger.UNSPECIFIED,
            entry_range=PriceRange(
                low=_p("150.00"),
                high=_p("150.50"),
            ),
            status=SignalStatus.PARTIAL,
            lifecycle_state=LifecycleState.DRAFT,
            created_at_utc=FIXED_TS,
        )
    if fixture == "E_MULTI_INSTRUCTION":
        return Signal(
            identity=identity,
            instrument=_instrument("EURUSD", AssetClass.FOREX),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=_p("1.1000"),
            stop_loss=_p("1.0950"),
            take_profit_targets=(_p("1.1100"), _p("1.1200")),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=FIXED_TS,
        )
    if fixture == "F_REVISION_CHAIN":
        return Signal(
            identity=identity,
            instrument=_instrument("EURUSD", AssetClass.FOREX),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=_p("1.1000"),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=FIXED_TS,
        )
    raise KeyError(f"Unknown fixture: {fixture}")


_INSTRUCTION_TYPES: tuple[InstructionType, ...] = (
    InstructionType.OPEN,
    InstructionType.MODIFY,
    InstructionType.MOVE_SL,
    InstructionType.MOVE_TP,
    InstructionType.BREAKEVEN,
    InstructionType.SCALE_IN,
    InstructionType.TRAIL,
    InstructionType.REVERSE,
)


def build_instruction(fixture: str, index: int = 0) -> SignalInstruction:
    """Build a deterministic SignalInstruction for the named fixture.

    The fixture determines the canonical payload content. The ``index``
    argument is reserved for instruction-fan-out scenarios and only
    matters for ``E_MULTI_INSTRUCTION``.
    """

    identity = build_identity()
    if fixture == "E_MULTI_INSTRUCTION":
        i_type = _INSTRUCTION_TYPES[index % len(_INSTRUCTION_TYPES)]
    elif fixture == "F_REVISION_CHAIN":
        i_type = InstructionType.MODIFY
    else:
        i_type = InstructionType.OPEN

    if i_type == InstructionType.OPEN:
        payload: tuple[tuple[str, Any], ...] = ()
    elif i_type == InstructionType.MODIFY:
        payload = (("field", "stop_loss"),)
    elif i_type == InstructionType.MOVE_SL:
        payload = (("new_sl", _p("1.0940")),)
    elif i_type == InstructionType.MOVE_TP:
        payload = (
            (
                "new_tp",
                (_p("1.1150"), _p("1.1250")),
            ),
        )
    elif i_type == InstructionType.BREAKEVEN:
        payload = ()
    elif i_type == InstructionType.SCALE_IN:
        payload = (("new_levels", (_p("1.0980"), _p("1.0970"))),)
    elif i_type == InstructionType.TRAIL:
        payload = (("trail_distance", Decimal("0.0020")),)
    elif i_type == InstructionType.REVERSE:
        payload = (("new_direction", TradeDirection.SELL),)
    elif i_type == InstructionType.CANCEL:
        payload = ()
    else:
        payload = ()

    return SignalInstruction(
        instruction_type=i_type,
        signal_identity=identity,
        payload=payload,
        created_at_utc=FIXED_TS,
    )


def build_canonical_snapshot(fixture: str) -> tuple[tuple[str, Any], ...]:
    """Build a deterministic canonical_snapshot for fingerprint benchmarks.

    For ``D_NESTED_SNAPSHOT`` we deliberately construct a snapshot whose
    values include nested tuples and Price objects. For other fixtures
    we use the canonical state of the corresponding Signal as a string-only
    projection (cheap to construct) — this isolates fingerprint cost from
    Signal construction cost.
    """

    if fixture == "D_NESTED_SNAPSHOT":
        return (
            ("direction", "BUY"),
            ("entry_geometry", "RANGE"),
            ("entry_trigger", "UNSPECIFIED"),
            ("entry_range", (("150.00",), ("150.50",))),
            ("status", "PARTIAL"),
            ("lifecycle_state", "DRAFT"),
        )
    if fixture == "C_LARGE_SIGNAL":
        levels = tuple((str(p),) for p in range(29000, 29012))
        tps = tuple((str(p),) for p in (30500, 31000, 31500, 32000))
        return (
            ("direction", "BUY"),
            ("entry_geometry", "MULTIPLE"),
            ("entry_trigger", "LIMIT"),
            ("entry_levels", levels),
            ("stop_loss", ("28800.00",)),
            ("take_profit_targets", tps),
            ("status", "COMPLETE"),
            ("lifecycle_state", "ACTIVE"),
            ("canonical_symbol", "BTCUSD"),
            ("asset_class", "CRYPTO"),
            ("created_at", "2024-06-15T12:00:00+00:00"),
            ("uuid_a", FIXED_LOGICAL_ID),
        )
    if fixture == "B_NORMAL_SIGNAL":
        return (
            ("direction", "BUY"),
            ("entry_geometry", "SINGLE"),
            ("entry_trigger", "LIMIT"),
            ("entry_price", ("1.1000",)),
            ("stop_loss", ("1.0950",)),
            ("take_profit_targets", (("1.1100",), ("1.1200",), ("1.1300",))),
            ("status", "COMPLETE"),
            ("lifecycle_state", "ACTIVE"),
            ("canonical_symbol", "EURUSD"),
            ("asset_class", "FOREX"),
        )
    if fixture == "A_MINIMAL_SIGNAL":
        return (
            ("direction", "BUY"),
            ("entry_geometry", "SINGLE"),
            ("entry_trigger", "LIMIT"),
            ("entry_price", ("1.1000",)),
            ("status", "COMPLETE"),
            ("lifecycle_state", "ACTIVE"),
            ("canonical_symbol", "EURUSD"),
        )
    if fixture == "F_REVISION_CHAIN":
        return (
            ("direction", "BUY"),
            ("entry_geometry", "SINGLE"),
            ("entry_trigger", "LIMIT"),
            ("entry_price", ("1.1000",)),
            ("status", "COMPLETE"),
            ("lifecycle_state", "ACTIVE"),
        )
    if fixture == "E_MULTI_INSTRUCTION":
        return (
            ("instruction_type", "OPEN"),
            ("payload_size", 0),
            ("status", "ACTIVE"),
            ("canonical_symbol", "EURUSD"),
        )
    raise KeyError(f"Unknown fixture: {fixture}")


def build_revision_chain(fixture: str) -> list[SignalRevision]:
    """Build a chain of revisions sharing the same logical identity.

    Returns the revisions in chronological order (rev1, rev2, rev3).
    """

    snapshot = build_canonical_snapshot(fixture)
    rev1 = SignalRevision(
        revision_id=FIXED_REVISION_ID_1,
        logical_signal_id=FIXED_LOGICAL_ID,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored_by_post_init",
        created_at_utc=FIXED_TS,
    )
    rev2 = SignalRevision(
        revision_id=FIXED_REVISION_ID_2,
        logical_signal_id=FIXED_LOGICAL_ID,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=snapshot,
        fingerprint="ignored_by_post_init",
        created_at_utc=FIXED_TS,
    )
    rev3 = SignalRevision(
        revision_id=FIXED_REVISION_ID_3,
        logical_signal_id=FIXED_LOGICAL_ID,
        revision_number=3,
        previous_revision_id=rev2.revision_id,
        canonical_snapshot=snapshot,
        fingerprint="ignored_by_post_init",
        created_at_utc=FIXED_TS,
    )
    return [rev1, rev2, rev3]


def build_event(fixture: str) -> SignalEvent:
    """Build a deterministic SignalEvent."""

    identity = build_identity()
    return SignalEvent(
        event_id=FIXED_EVENT_ID,
        signal_identity=identity,
        event_type=EventType.REVISED,
        timestamp_utc=FIXED_TS,
        previous_revision_id=FIXED_REVISION_ID_1,
        new_revision_id=FIXED_REVISION_ID_2,
        event_payload=(
            ("prev_status", "PARTIAL"),
            ("new_status", "COMPLETE"),
        ),
        provenance=_provider_source(),
    )


@dataclass(frozen=True)
class ScaleSpec:
    """Snapshot-size scaling point."""

    label: str
    snapshot: tuple[tuple[str, Any], ...]


def build_fingerprint_scaling_points() -> list[ScaleSpec]:
    """Return a list of canonical snapshots with increasing size.

    Used by the fingerprint-scaling benchmark to measure cost as a
    function of canonical snapshot size (number of (key, value) pairs
    and total leaf items after normalization).
    """

    small = (
        ("direction", "BUY"),
        ("status", "COMPLETE"),
    )
    medium = (
        ("direction", "BUY"),
        ("entry_geometry", "SINGLE"),
        ("entry_trigger", "LIMIT"),
        ("entry_price", ("1.1000",)),
        ("status", "COMPLETE"),
        ("lifecycle_state", "ACTIVE"),
        ("canonical_symbol", "EURUSD"),
        ("asset_class", "FOREX"),
    )
    large_levels = tuple((f"level_{i}", ((str(1000 + i),),)) for i in range(20))
    large = (
        ("direction", "BUY"),
        ("entry_geometry", "MULTIPLE"),
        ("entry_trigger", "LIMIT"),
        ("entry_levels", large_levels),
        ("stop_loss", ("950.00",)),
        ("take_profit_targets", tuple((str(1100 + i),) for i in range(10))),
        ("status", "COMPLETE"),
        ("lifecycle_state", "ACTIVE"),
        ("canonical_symbol", "BTCUSD"),
        ("asset_class", "CRYPTO"),
        ("created_at", "2024-06-15T12:00:00+00:00"),
        ("uuid_a", FIXED_LOGICAL_ID),
    )
    xl_levels = tuple((f"level_{i}", ((str(2000 + i),),)) for i in range(100))
    xl = (
        ("direction", "BUY"),
        ("entry_geometry", "MULTIPLE"),
        ("entry_trigger", "LIMIT"),
        ("entry_levels", xl_levels),
        ("stop_loss", ("1900.00",)),
        ("take_profit_targets", tuple((str(2100 + i),) for i in range(20))),
        ("status", "COMPLETE"),
        ("lifecycle_state", "ACTIVE"),
        ("canonical_symbol", "ETHUSD"),
        ("asset_class", "CRYPTO"),
        ("created_at", "2024-06-15T12:00:00+00:00"),
        ("uuid_a", FIXED_LOGICAL_ID),
    )
    return [
        ScaleSpec(label="small", snapshot=small),
        ScaleSpec(label="medium", snapshot=medium),
        ScaleSpec(label="large", snapshot=large),
        ScaleSpec(label="xlarge", snapshot=xl),
    ]


__all__ = [
    "FIXED_EVENT_ID",
    "FIXED_LOGICAL_ID",
    "FIXED_PROVIDER_REF",
    "FIXED_REVISION_ID_1",
    "FIXED_REVISION_ID_2",
    "FIXED_REVISION_ID_3",
    "FIXED_TS",
    "FIXTURES",
    "FixtureSpec",
    "ScaleSpec",
    "build_canonical_snapshot",
    "build_event",
    "build_fingerprint_scaling_points",
    "build_identity",
    "build_instruction",
    "build_revision_chain",
    "build_signal",
]
