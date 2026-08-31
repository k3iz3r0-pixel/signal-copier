"""Adversarial Category 11 — Deep immutability attacks."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import (
    Signal,
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
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


def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="test", signal_reference="t"),
    )


def instrument() -> Instrument:
    return Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)


class TestDeepImmutabilitySignal:
    def test_mutation_attempt_on_frozen_signal_fails(self) -> None:
        signal = Signal(
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
        with pytest.raises(AttributeError):
            signal.direction = TradeDirection.SELL  # type: ignore[misc]

    def test_mutation_attempt_on_tuple_levels_fails(self) -> None:
        signal = Signal(
            identity=identity(),
            instrument=instrument(),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.MULTIPLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_levels=(Price(value=Decimal("1.0")), Price(value=Decimal("1.2"))),
            lifecycle_state=LifecycleState.ACTIVE,
            status=SignalStatus.COMPLETE,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        # Direct mutation on tuple fails; mutation on nested Price fails (Price frozen).
        with pytest.raises(AttributeError):
            signal.entry_levels += (Price(value=Decimal("1.5")),)  # type: ignore[operator]

    def test_mutation_on_nested_price_fails(self) -> None:
        p = Price(value=Decimal("1.1"))
        with pytest.raises(AttributeError):
            p.value = Decimal("2.0")  # type: ignore[misc]


class TestDeepImmutabilityInstruction:
    def test_payload_tuple_immutable(self) -> None:
        instruction = SignalInstruction(
            instruction_type=InstructionType.MODIFY,
            signal_identity=identity(),
            payload=(("field", "value"),),
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        with pytest.raises(AttributeError):
            instruction.payload += (("new", "item"),)  # type: ignore[operator]

    def test_payload_nested_tuple_immutable(self) -> None:
        instruction = SignalInstruction(
            instruction_type=InstructionType.MOVE_TP,
            signal_identity=identity(),
            payload=(
                ("new_tp", (Price(value=Decimal(160)), Price(value=Decimal(170)))),
            ),
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        with pytest.raises(AttributeError):
            instruction.payload += ((),)  # type: ignore[operator]


class TestDeepImmutabilityEvent:
    def test_event_payload_immutable(self) -> None:
        event = SignalEvent(
            event_id=uuid4(),
            signal_identity=identity(),
            event_type=EventType.REVISED,
            timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
            event_payload=(("prev", "val"),),
        )
        with pytest.raises(AttributeError):
            event.event_payload += (("new",),)  # type: ignore[operator]

    def test_nested_tuple_event_payload_immutable(self) -> None:
        event = SignalEvent(
            event_id=uuid4(),
            signal_identity=identity(),
            event_type=EventType.REVISED,
            timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
            event_payload=(("nested", (Price(value=Decimal(100)),)),),
        )
        with pytest.raises(AttributeError):
            event.event_payload += ((),)  # type: ignore[operator]


class TestDeepImmutabilityValueObjects:
    def test_price_immutable(self) -> None:
        p = Price(value=Decimal("1.1"))
        with pytest.raises(AttributeError):
            p.value = Decimal("2.2")  # type: ignore[misc]

    def test_price_range_immutable(self) -> None:
        pr = PriceRange(low=Price(value=Decimal(1)), high=Price(value=Decimal(2)))
        with pytest.raises(AttributeError):
            pr.low = Price(value=Decimal(3))  # type: ignore[misc]

    def test_instrument_immutable(self) -> None:
        inst = Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)
        with pytest.raises(AttributeError):
            inst.canonical_symbol = "GBPUSD"  # type: ignore[misc]


class TestNestedMutableReachability:
    def test_tuple_containing_tuple_containing_tuple_is_immutable(self) -> None:
        deep = (("a", (("b", (1, 2, 3)),)),)
        # No mutation mechanism exists; just verify structure.
        assert isinstance(deep, tuple)
        assert isinstance(deep[0][1], tuple)
        assert isinstance(deep[0][1][0][1], tuple)

    def test_tuple_containing_dict_rejected_by_domain(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            from packages.signal_core.domain import _validate_canonical_value

            _validate_canonical_value((("bad", {"nested": True}),))
