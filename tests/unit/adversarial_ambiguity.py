"""Adversarial Category 5 — Ambiguity / partial / unspecified attacks."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import Signal, SignalIdentity
from packages.signal_core.enums import (
    AssetClass,
    EntryGeometry,
    EntryTrigger,
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


def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="test", signal_reference="t"),
    )


def instrument() -> Instrument:
    return Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)


class TestAmbiguousStatus:
    def test_ambiguous_requires_draft_lifecycle(self) -> None:
        with pytest.raises(ValueError, match="DRAFT"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MARKET,
                entry_trigger=EntryTrigger.UNSPECIFIED,
                status=SignalStatus.AMBIGUOUS,
                lifecycle_state=LifecycleState.ACTIVE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_ambiguous_with_draft_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.MARKET,
            entry_trigger=EntryTrigger.UNSPECIFIED,
            status=SignalStatus.AMBIGUOUS,
            lifecycle_state=LifecycleState.DRAFT,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.status == SignalStatus.AMBIGUOUS
        assert signal.lifecycle_state == LifecycleState.DRAFT

    def test_partial_with_active_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.MARKET,
            entry_trigger=EntryTrigger.UNSPECIFIED,
            status=SignalStatus.PARTIAL,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.status == SignalStatus.PARTIAL

    def test_complete_with_draft_accepted(self) -> None:
        # Design allows COMPLETE + DRAFT? Not explicitly forbidden in structural invariants.
        # This verifies current behavior without inventing a restriction.
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal("1.1")),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.DRAFT,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.lifecycle_state == LifecycleState.DRAFT

    def test_ambiguous_with_missing_fields_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.MARKET,
            entry_trigger=EntryTrigger.UNSPECIFIED,
            status=SignalStatus.AMBIGUOUS,
            lifecycle_state=LifecycleState.DRAFT,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.entry_price is None
        assert signal.entry_range is None


class TestUnspecifiedTriggerPreserved:
    def test_unspecified_not_promoted_to_market_single(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.UNSPECIFIED,
            entry_price=Price(value=Decimal("1.1")),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.entry_trigger == EntryTrigger.UNSPECIFIED

    def test_unspecified_not_promoted_to_market_range(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.RANGE,
            entry_trigger=EntryTrigger.UNSPECIFIED,
            entry_range=PriceRange(
                low=Price(value=Decimal("1.0")), high=Price(value=Decimal("1.2"))
            ),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.entry_trigger == EntryTrigger.UNSPECIFIED


class TestPartialSignalPreservation:
    def test_partial_signal_with_missing_sl_and_tp_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal("1.1")),
            status=SignalStatus.PARTIAL,
            lifecycle_state=LifecycleState.DRAFT,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.status == SignalStatus.PARTIAL
        assert signal.stop_loss is None
        assert signal.take_profit_targets == ()
