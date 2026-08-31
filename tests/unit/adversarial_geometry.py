"""Adversarial Category 3 — Entry geometry attacks."""
from packages.signal_core.enums import AssetClass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import Signal
from packages.signal_core.enums import (
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

from packages.signal_core.domain import SignalIdentity


def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="test", signal_reference="t"),
    )


def instrument() -> Instrument:
    return Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)


class TestMarketGeometryAdversarial:
    def test_market_with_price_fails(self) -> None:
        with pytest.raises(ValueError, match="MARKET"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MARKET,
                entry_trigger=EntryTrigger.MARKET,
                entry_price=Price(value=Decimal("1.1")),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_market_with_range_fails(self) -> None:
        with pytest.raises(ValueError, match="MARKET"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MARKET,
                entry_trigger=EntryTrigger.MARKET,
                entry_range=PriceRange(low=Price(value=Decimal("1")), high=Price(value=Decimal("2"))),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_market_with_levels_fails(self) -> None:
        with pytest.raises(ValueError, match="MARKET"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MARKET,
                entry_trigger=EntryTrigger.MARKET,
                entry_levels=(Price(value=Decimal("1")),),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )


class TestSingleGeometryAdversarial:
    def test_single_missing_price_fails(self) -> None:
        with pytest.raises(ValueError, match="SINGLE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_single_with_range_fails(self) -> None:
        with pytest.raises(ValueError, match="SINGLE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                entry_range=PriceRange(low=Price(value=Decimal("1")), high=Price(value=Decimal("2"))),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_single_with_multiple_levels_fails(self) -> None:
        with pytest.raises(ValueError, match="SINGLE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                entry_levels=(Price(value=Decimal("1.0")),),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )


class TestRangeGeometryAdversarial:
    def test_range_missing_range_fails(self) -> None:
        with pytest.raises(ValueError, match="RANGE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.RANGE,
                entry_trigger=EntryTrigger.LIMIT,
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_range_with_entry_price_fails(self) -> None:
        with pytest.raises(ValueError, match="RANGE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.RANGE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                entry_range=PriceRange(low=Price(value=Decimal("1")), high=Price(value=Decimal("2"))),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )


class TestMultipleGeometryAdversarial:
    def test_multiple_empty_levels_fails(self) -> None:
        with pytest.raises(ValueError, match="MULTIPLE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MULTIPLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_levels=(),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_multiple_unordered_ascending_fails(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MULTIPLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_levels=(
                    Price(value=Decimal("2")),
                    Price(value=Decimal("1")),
                ),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_multiple_duplicate_levels_fails(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MULTIPLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_levels=(
                    Price(value=Decimal("1")),
                    Price(value=Decimal("1")),
                ),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_multiple_with_entry_price_fails(self) -> None:
        with pytest.raises(ValueError, match="MULTIPLE"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MULTIPLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                entry_levels=(Price(value=Decimal("1.0")), Price(value=Decimal("1.2"))),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )
