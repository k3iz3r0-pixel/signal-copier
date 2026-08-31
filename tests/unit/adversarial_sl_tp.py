"""Adversarial Category 4 — Stop Loss / Take Profit attacks."""
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


class TestStopLossAdversarial:
    def test_buy_sl_must_be_less_than_entry(self) -> None:
        with pytest.raises(ValueError, match="stop_loss"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                stop_loss=Price(value=Decimal("1.2")),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_buy_sl_at_entry_fails(self) -> None:
        with pytest.raises(ValueError, match="stop_loss"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                stop_loss=Price(value=Decimal("1.1")),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_buy_sl_less_than_entry_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal("1.1")),
            stop_loss=Price(value=Decimal("1.05")),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.stop_loss.value == Decimal("1.05")

    def test_sell_sl_must_be_greater_than_entry(self) -> None:
        with pytest.raises(ValueError, match="stop_loss"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.SELL,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                stop_loss=Price(value=Decimal("1.0")),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_no_sl_accepted_for_buy_and_sell(self) -> None:
        signal_buy = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal("1.1")),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal_buy.stop_loss is None


class TestTakeProfitAdversarial:
    def test_buy_tp_must_ascend(self) -> None:
        with pytest.raises(ValueError, match="invariant"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                take_profit_targets=(
                    Price(value=Decimal("1.15")),
                    Price(value=Decimal("1.05")),
                ),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_buy_tp_must_be_at_or_above_entry(self) -> None:
        with pytest.raises(ValueError, match="TP"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                take_profit_targets=(Price(value=Decimal("1.0")),),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_buy_tp_duplicate_rejected(self) -> None:
        with pytest.raises(ValueError, match="invariant"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                take_profit_targets=(
                    Price(value=Decimal("1.2")),
                    Price(value=Decimal("1.2")),
                ),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_buy_tp_ascending_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal("1.1")),
            take_profit_targets=(
                Price(value=Decimal("1.15")),
                Price(value=Decimal("1.20")),
            ),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert len(signal.take_profit_targets) == 2

    def test_sell_tp_must_descend(self) -> None:
        with pytest.raises(ValueError, match="invariant"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.SELL,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                take_profit_targets=(
                    Price(value=Decimal("1.05")),
                    Price(value=Decimal("1.15")),
                ),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_sell_tp_must_be_at_or_below_entry(self) -> None:
        with pytest.raises(ValueError, match="TP"):
            Signal(
                identity=identity(),
                instrument=instrument(),
                direction=TradeDirection.SELL,
                entry_geometry=EntryGeometry.SINGLE,
                entry_trigger=EntryTrigger.LIMIT,
                entry_price=Price(value=Decimal("1.1")),
                take_profit_targets=(Price(value=Decimal("1.2")),),
                lifecycle_state=LifecycleState.ACTIVE,
                status=SignalStatus.COMPLETE,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_empty_tp_accepted(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal("1.1")),
            take_profit_targets=(),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert signal.take_profit_targets == ()
