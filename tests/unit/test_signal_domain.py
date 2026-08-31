import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import Signal, SignalIdentity
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


# Helper fixtures
@pytest.fixture
def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(
            provider_name="provider_alpha", signal_reference="ref-001"
        ),
    )


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(
        canonical_symbol="EURUSD",
        asset_class=__import__(
            "packages.signal_core.enums", fromlist=["AssetClass"]
        ).AssetClass.FOREX,
    )


# A. Minimal valid Signal


def test_minimal_valid_signal(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.1000")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    assert signal.direction == TradeDirection.BUY
    assert signal.entry_price is not None
    assert signal.entry_price.value == Decimal("1.1000")


# B. BUY market signal


def test_buy_market(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="GBPUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.MARKET,
        entry_trigger=EntryTrigger.MARKET,
        entry_price=None,
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert signal.entry_geometry == EntryGeometry.MARKET
    assert signal.entry_price is None
    assert signal.entry_trigger == EntryTrigger.MARKET


# C. SELL market signal


def test_sell_market(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="USDJPY", asset_class=AssetClass.FOREX),
        direction=TradeDirection.SELL,
        entry_geometry=EntryGeometry.MARKET,
        entry_trigger=EntryTrigger.MARKET,
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 6, 15, 8, 30, 0, tzinfo=UTC),
    )
    assert signal.direction == TradeDirection.SELL


# D. BUY LIMIT


def test_buy_limit_single_price(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.0950")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.entry_geometry == EntryGeometry.SINGLE
    assert signal.entry_trigger == EntryTrigger.LIMIT


# E. BUY STOP


def test_buy_stop_single_price(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(
            canonical_symbol="XAUUSD", asset_class=AssetClass.COMMODITY
        ),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.STOP,
        entry_price=Price(value=Decimal("2050.50")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.entry_trigger == EntryTrigger.STOP


# F. SELL LIMIT


def test_sell_limit_single_price(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="AUDUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.SELL,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("0.6720")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.direction == TradeDirection.SELL


# G. SELL STOP


def test_sell_stop_single_price(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="USDCHF", asset_class=AssetClass.FOREX),
        direction=TradeDirection.SELL,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.STOP,
        entry_price=Price(value=Decimal("0.9150")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )


# H. Explicit UNSPECIFIED trigger


def test_explicit_unspecified_trigger(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="BTCUSD", asset_class=AssetClass.CRYPTO),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.UNSPECIFIED,
        entry_price=Price(value=Decimal(3350)),
        status=SignalStatus.PARTIAL,
        lifecycle_state=LifecycleState.DRAFT,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.entry_trigger == EntryTrigger.UNSPECIFIED
    assert signal.entry_trigger is not EntryTrigger.MARKET


# I. Single-price entry


def test_single_price_entry(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="ETHUSD", asset_class=AssetClass.CRYPTO),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.UNSPECIFIED,
        entry_price=Price(value=Decimal("3500.25")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.entry_geometry == EntryGeometry.SINGLE
    assert signal.entry_price.value == Decimal("3500.25")


# J. Entry range


def test_entry_range(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(
            canonical_symbol="XAUUSD", asset_class=AssetClass.COMMODITY
        ),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.RANGE,
        entry_trigger=EntryTrigger.UNSPECIFIED,
        entry_range=PriceRange(
            low=Price(value=Decimal("150.00")), high=Price(value=Decimal("150.50"))
        ),
        status=SignalStatus.PARTIAL,
        lifecycle_state=LifecycleState.DRAFT,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.entry_range is not None
    assert signal.entry_range.low.value == Decimal("150.00")
    assert signal.entry_range.high.value == Decimal("150.50")


# K. Multiple entry levels


def test_multiple_entry_levels(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="BTCUSD", asset_class=AssetClass.CRYPTO),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.MULTIPLE,
        entry_trigger=EntryTrigger.UNSPECIFIED,
        entry_levels=(
            Price(value=Decimal("146.00")),
            Price(value=Decimal("148.00")),
            Price(value=Decimal("150.00")),
        ),
        stop_loss=Price(value=Decimal("144.00")),
        take_profit_targets=(
            Price(value=Decimal("160.00")),
            Price(value=Decimal("170.00")),
        ),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert len(signal.entry_levels) == 3
    assert signal.entry_price is None


# L. Stop loss


def test_stop_loss_present(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.1000")),
        stop_loss=Price(value=Decimal("1.0950")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.stop_loss.value == Decimal("1.0950")


# M. Multiple take-profit targets


def test_multiple_take_profit_targets(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="USDJPY", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("110.50")),
        take_profit_targets=(
            Price(value=Decimal("111.00")),
            Price(value=Decimal("111.50")),
        ),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert len(signal.take_profit_targets) == 2


# N. Missing optional SL (None)


def test_missing_stop_loss_explicit_absence(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="GBPUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.MARKET,
        entry_trigger=EntryTrigger.MARKET,
        stop_loss=None,
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.stop_loss is None


# O. Missing optional TP (empty tuple)


def test_missing_take_profit_empty_tuple(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="AUDUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("0.6500")),
        take_profit_targets=(),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.take_profit_targets == ()
    assert signal.take_profit_targets is not None


# P. Equality


def test_signal_equality(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    s1 = Signal(
        identity=identity,
        instrument=Instrument(
            canonical_symbol="XAUUSD", asset_class=AssetClass.COMMODITY
        ),
        direction=TradeDirection.SELL,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.STOP,
        entry_price=Price(value=Decimal(1900)),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    s2 = Signal(
        identity=identity,
        instrument=Instrument(
            canonical_symbol="XAUUSD", asset_class=AssetClass.COMMODITY
        ),
        direction=TradeDirection.SELL,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.STOP,
        entry_price=Price(value=Decimal(1900)),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert s1 == s2


# Q. Hashing


def test_signal_hash_stable(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    s = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.MARKET,
        entry_trigger=EntryTrigger.MARKET,
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    h = hash(s)
    assert isinstance(h, int)
    # Hash must be deterministic (same object, same hash)
    assert hash(s) == h


# R. Deep immutability


def test_deep_immutability(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    s = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="BTCUSD", asset_class=AssetClass.CRYPTO),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.MULTIPLE,
        entry_trigger=EntryTrigger.UNSPECIFIED,
        entry_levels=(Price(value=Decimal(150)),),
        status=SignalStatus.PARTIAL,
        lifecycle_state=LifecycleState.DRAFT,
        created_at_utc=datetime.now(UTC),
    )
    # Frozen dataclass prevents mutation
    with pytest.raises(AttributeError):
        s.direction = TradeDirection.SELL  # type: ignore[misc]
    # Tuple immutability (frozen dataclass raises FrozenInstanceError)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.entry_levels += (Price(value=Decimal(140)),)  # type: ignore[operator]


# S. Invalid instrument (empty symbol)


def test_invalid_instrument_empty_symbol(identity: SignalIdentity) -> None:
    with pytest.raises(ValueError):
        Signal(
            identity=identity,
            instrument=Instrument(
                canonical_symbol="",
                asset_class=__import__(
                    "packages.signal_core.enums", fromlist=["AssetClass"]
                ).AssetClass.FOREX,
            ),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.MARKET,
            entry_trigger=EntryTrigger.MARKET,
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime.now(UTC),
        )


# T. Invalid direction


def test_invalid_direction_type(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    with pytest.raises(TypeError):
        Signal(
            identity=identity,
            instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
            direction="BUY",
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal(1)),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime.now(UTC),
        )


# U. Invalid entry combinations (SINGLE without price)


def test_invalid_single_without_price(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    with pytest.raises(ValueError):
        Signal(
            identity=identity,
            instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=None,
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime.now(UTC),
        )


# V. Invalid price relationships (BUY SL >= entry)


def test_invalid_buy_sl_not_less_than_entry(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    with pytest.raises(ValueError):
        Signal(
            identity=identity,
            instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal(100)),
            stop_loss=Price(value=Decimal(100)),  # SL == entry — invalid
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime.now(UTC),
        )


# W. No broker/provider leakage


def test_no_broker_fields_in_signal(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.1")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    # Signal must not expose broker_reference, lot_size, account, etc.
    assert not hasattr(signal, "broker_reference")
    assert not hasattr(signal, "lot_size")
    assert not hasattr(signal, "order_id")


# X. Logical identity independent of mutable content


def test_identity_independent_of_content() -> None:
    from packages.signal_core.enums import AssetClass

    logical_id = uuid4()
    id_ref = SignalIdentity(
        logical_signal_id=logical_id,
        provider_identity=ProviderSource(
            provider_name="provider_alpha", signal_reference="ref-001"
        ),
    )
    # Same logical identity used in two Signals with different canonical content
    signal_a = Signal(
        identity=id_ref,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.1000")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    signal_b = Signal(
        identity=id_ref,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.STOP,
        entry_price=Price(value=Decimal("1.1050")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 6, 1, 10, 0, 0, tzinfo=UTC),
    )
    # Same logical identity preserved despite different content
    assert signal_a.identity.logical_signal_id == signal_b.identity.logical_signal_id
    assert signal_a.identity.logical_signal_id == logical_id
    # Content differences: different trigger, different entry price, different timestamp
    assert signal_a.entry_trigger != signal_b.entry_trigger
    assert signal_a.entry_price.value != signal_b.entry_price.value
    assert signal_a.created_at_utc != signal_b.created_at_utc


# Y. Boundary values


def test_price_boundary_zero(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    # Boundary: explicit zero price is valid (Decimal("0.0"))
    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.MARKET,
        entry_price=Price(value=Decimal("0.0")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime.now(UTC),
    )
    assert signal.entry_price.value == Decimal("0.0")


# Entry compatibility matrix (canonical domain: geometry + trigger independent, UNSPECIFIED preserved)


def test_entry_compatibility_matrix(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    # All geometry/trigger combinations are semantically independent in core.
    # Critical rule: UNSPECIFIED must never become MARKET automatically.
    signal_unspecified = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.UNSPECIFIED,
        entry_price=Price(value=Decimal(3350)),
        status=SignalStatus.PARTIAL,
        lifecycle_state=LifecycleState.DRAFT,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert signal_unspecified.entry_trigger == EntryTrigger.UNSPECIFIED
    assert signal_unspecified.entry_trigger.name == "UNSPECIFIED"
    # MARKET trigger preserved independently
    signal_market = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.MARKET,
        entry_trigger=EntryTrigger.MARKET,
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert signal_market.entry_trigger == EntryTrigger.MARKET


# Z. Decimal behavior


def test_decimal_behavior_in_prices() -> None:
    p1 = Price(value=Decimal("10.500"))
    p2 = Price(value=Decimal("10.5"))
    assert p1.value == p2.value
    assert p1 == p2  # equality uses Decimal equality, which normalizes


# UTC datetime validation


def test_utc_aware_accepted(identity: SignalIdentity) -> None:
    from packages.signal_core.enums import AssetClass

    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal(1)),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert signal.created_at_utc.tzinfo is not None


def test_naive_datetime_rejected(identity: SignalIdentity) -> None:

    from packages.signal_core.enums import AssetClass

    with pytest.raises(ValueError, match="timezone-aware"):
        Signal(
            identity=identity,
            instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal(1)),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0),  # noqa: DTZ001
        )


def test_non_utc_aware_rejected(identity: SignalIdentity) -> None:
    import datetime

    from packages.signal_core.enums import AssetClass

    with pytest.raises(ValueError, match="UTC"):
        Signal(
            identity=identity,
            instrument=Instrument(canonical_symbol="X", asset_class=AssetClass.OTHER),
            direction=TradeDirection.BUY,
            entry_geometry=EntryGeometry.SINGLE,
            entry_trigger=EntryTrigger.LIMIT,
            entry_price=Price(value=Decimal(1)),
            status=SignalStatus.COMPLETE,
            lifecycle_state=LifecycleState.ACTIVE,
            created_at_utc=datetime.datetime(
                2024,
                1,
                1,
                0,
                0,
                0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=5)),
            ),
        )
