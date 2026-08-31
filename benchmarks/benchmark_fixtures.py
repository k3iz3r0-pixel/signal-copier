"""Benchmark fixtures for Phase 1 Step 9 — performance baseline.
Standard library only; deterministic inputs; no new dependencies."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from packages.signal_core.domain import (
    Signal,
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    canonical_fingerprint,
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


# Fixture A: Minimal signal (smallest valid)
MINIMAL_SIGNAL = Signal(
    identity=SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="min", signal_reference="m1"),
    ),
    instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
    direction=TradeDirection.BUY,
    entry_geometry=EntryGeometry.MARKET,
    entry_trigger=EntryTrigger.MARKET,
    lifecycle_state=LifecycleState.DRAFT,
    status=SignalStatus.PARTIAL,
    created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
)

# Fixture B: Normal signal (representative full signal)
NORMAL_SIGNAL = Signal(
    identity=SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="norm", signal_reference="n1"),
    ),
    instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
    direction=TradeDirection.BUY,
    entry_geometry=EntryGeometry.SINGLE,
    entry_trigger=EntryTrigger.LIMIT,
    entry_price=Price(value=Decimal("1.1000")),
    entry_range=None,
    entry_levels=(),
    stop_loss=Price(value=Decimal("1.0950")),
    take_profit_targets=(
        Price(value=Decimal("1.1100")),
        Price(value=Decimal("1.1150")),
    ),
    status=SignalStatus.COMPLETE,
    lifecycle_state=LifecycleState.ACTIVE,
    revision_reference_id=uuid4(),
    created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
)

# Fixture C: Large canonical snapshot (many fields in snapshot)
LARGE_SNAPSHOT = tuple(
    (f"field_{i}", Price(value=Decimal(str(i))))
    for i in range(1, 51)
)

# Fixture D: Deep nested canonical snapshot
NESTED_SNAPSHOT = (
    ("nested", (
        ("level2", (Price(value=Decimal("100")), Price(value=Decimal("150")))),
        ("level3", (("deep", Price(value=Decimal("200"))),)),
    )),
)

# Fixture E: Multi-instruction (several instructions referencing same identity)
IDENTITY_E = SignalIdentity(
    logical_signal_id=uuid4(),
    provider_identity=ProviderSource(provider_name="multi", signal_reference="e1"),
)
INSTRUCTIONS_E = tuple(
    SignalInstruction(
        instruction_type=it,
        signal_identity=IDENTITY_E,
        created_at_utc=datetime(2024, ((i % 12) + 1), 1, 0, 0, 0, tzinfo=UTC),
    )
    for i, it in enumerate(InstructionType)
)

# Fixture F: Revision chain (5 revisions, same logical identity)
LOGICAL_F = uuid4()
_REV_PREVIOUS = None
_REVISION_CHAIN_LIST = []
for i in range(1, 6):
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=LOGICAL_F,
        revision_number=i,
        previous_revision_id=_REV_PREVIOUS,
        canonical_snapshot=(("step", i), ("price", Price(value=Decimal(str(i * 10))))),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 1, i, 0, 0, 0, tzinfo=UTC),
    )
    _REVISION_CHAIN_LIST.append(rev)
    _REV_PREVIOUS = rev.revision_id
REVISION_CHAIN_F = tuple(_REVISION_CHAIN_LIST)

# Fixture for fingerprint scaling
SNAPSHOTS_SMALL = (("k", Price(value=Decimal("1"))),)
SNAPSHOTS_MEDIUM = tuple(
    (f"k{i}", Price(value=Decimal(str(i)))) for i in range(1, 21)
)
SNAPSHOTS_LARGE = tuple(
    (f"k{i}", Price(value=Decimal(str(i * 0.01)))) for i in range(1, 101)
)
