from datetime import UTC, datetime
from decimal import Decimal

import pytest

from packages.signal_core.enums import (
    AssetClass,
    EntryGeometry,
    EntryTrigger,
    EventType,
    LifecycleState,
    SignalStatus,
    SourceType,
    TradeDirection,
)
from packages.signal_core.value_objects import (
    Instrument,
    Price,
    PriceRange,
    ProviderSource,
    SourceIdentity,
)

# --- TradeDirection ---


def test_trade_direction_members() -> None:
    assert TradeDirection.BUY.value == "BUY"
    assert TradeDirection.SELL.value == "SELL"


def test_trade_direction_equality() -> None:
    assert TradeDirection.BUY == TradeDirection.BUY
    assert TradeDirection.BUY is not TradeDirection.SELL


# --- EntryGeometry ---


def test_entry_geometry_members() -> None:
    assert EntryGeometry.MARKET.value == "MARKET"
    assert EntryGeometry.SINGLE.value == "SINGLE"
    assert EntryGeometry.RANGE.value == "RANGE"
    assert EntryGeometry.MULTIPLE.value == "MULTIPLE"


# --- EntryTrigger ---


def test_entry_trigger_members() -> None:
    assert EntryTrigger.MARKET.value == "MARKET"
    assert EntryTrigger.LIMIT.value == "LIMIT"
    assert EntryTrigger.STOP.value == "STOP"
    assert EntryTrigger.UNSPECIFIED.value == "UNSPECIFIED"


def test_unspecified_distinct_from_market() -> None:
    """UNSPECIFIED must be distinct from MARKET per design."""
    assert EntryTrigger.UNSPECIFIED is not EntryTrigger.MARKET
    assert EntryTrigger.UNSPECIFIED.value != EntryTrigger.MARKET.value


# --- LifecycleState ---


def test_lifecycle_state_members() -> None:
    members = {
        LifecycleState.DRAFT,
        LifecycleState.ACTIVE,
        LifecycleState.CANCELLED,
        LifecycleState.EXPIRED,
        LifecycleState.ARCHIVED,
    }
    assert members == {
        LifecycleState.DRAFT,
        LifecycleState.ACTIVE,
        LifecycleState.CANCELLED,
        LifecycleState.EXPIRED,
        LifecycleState.ARCHIVED,
    }


def test_no_executing_or_executed_in_lifecycle() -> None:
    """EXECUTING and EXECUTED must NOT exist in LifecycleState."""
    names = {m.name for m in LifecycleState}
    assert "EXECUTING" not in names
    assert "EXECUTED" not in names


# --- SignalStatus ---


def test_signal_status_members() -> None:
    assert SignalStatus.PARTIAL.value == "PARTIAL"
    assert SignalStatus.COMPLETE.value == "COMPLETE"
    assert SignalStatus.AMBIGUOUS.value == "AMBIGUOUS"


# --- SourceType ---


def test_source_type_members() -> None:
    assert SourceType.TELEGRAM.value == "TELEGRAM"
    assert SourceType.DISCORD.value == "DISCORD"
    assert SourceType.MANUAL.value == "MANUAL"
    assert SourceType.API.value == "API"


# --- EventType ---


def test_event_type_has_required_categories() -> None:
    names = {e.name for e in EventType}
    assert "CREATED" in names
    assert "CANCELLED" in names
    assert "REVISED" in names
    assert "EXECUTING" in names
    assert "EXECUTED" in names
    assert "SCALE_IN" in names
    assert "SCALE_OUT" in names


# --- AssetClass ---


def test_asset_class_members() -> None:
    assert AssetClass.FOREX.value == "FOREX"
    assert AssetClass.CRYPTO.value == "CRYPTO"


# --- Price ---


def test_price_valid_construction() -> None:
    p = Price(value=Decimal("1.2345"))
    assert p.value == Decimal("1.2345")
    assert p.currency is None


def test_price_explicit_zero_is_meaningful() -> None:
    """Explicit zero (Decimal('0.0')) is a valid price, not absence."""
    p = Price(value=Decimal("0.0"))
    assert p.value == Decimal("0.0")


def test_price_with_currency() -> None:
    p = Price(value=Decimal("100.00"), currency="USD")
    assert p.currency == "USD"


def test_price_rejects_float() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        Price(value=1.2345)


def test_price_rejects_string() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        Price(value="1.23")


def test_price_immutable() -> None:
    p = Price(value=Decimal("99.99"))
    with pytest.raises(AttributeError):
        p.value = Decimal(0)


def test_price_equality_and_hash() -> None:
    p1 = Price(value=Decimal("10.5"))
    p2 = Price(value=Decimal("10.5"))
    p3 = Price(value=Decimal("10.500"))
    assert p1 == p2
    assert hash(p1) == hash(p2)
    # Normalized equality: Decimal('10.5') == Decimal('10.500')
    assert p1 == p3
    assert hash(p1) == hash(p3)


def test_price_boundary_values() -> None:
    p_large = Price(value=Decimal("9999999999.999999"))
    p_negative = Price(value=Decimal("-5.5"))
    assert p_large.value > 0
    assert p_negative.value < 0


# --- PriceRange ---


def test_price_range_valid() -> None:
    low = Price(value=Decimal(100))
    high = Price(value=Decimal(200))
    pr = PriceRange(low=low, high=high)
    assert pr.low == low
    assert pr.high == high


def test_price_range_none_fields() -> None:
    # PriceRange must have at least one boundary present per Step 2.1 correction.
    # Incomplete/ambiguous range is represented by omitting entry_range at Signal level,
    # not by an empty PriceRange.
    with pytest.raises(ValueError, match="at least one boundary"):
        PriceRange()


def test_price_range_immutable() -> None:
    pr = PriceRange(low=Price(value=Decimal(10)))
    with pytest.raises(AttributeError):
        pr.low = None


def test_price_range_equality() -> None:
    p1 = PriceRange(low=Price(value=Decimal(10)), high=Price(value=Decimal(20)))
    p2 = PriceRange(low=Price(value=Decimal(10)), high=Price(value=Decimal(20)))
    assert p1 == p2


# --- ProviderSource ---


def test_provider_source_valid() -> None:
    ps = ProviderSource(
        provider_name="provider_alpha",
        signal_reference="ref-001",
    )
    assert ps.provider_name == "provider_alpha"
    assert ps.signal_reference == "ref-001"
    assert ps.ingestion_timestamp_utc is None


def test_provider_source_with_timestamp() -> None:
    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    ps = ProviderSource(
        provider_name="provider_beta",
        signal_reference="ref-002",
        ingestion_timestamp_utc=ts,
    )
    assert ps.ingestion_timestamp_utc == ts


def test_provider_source_rejects_empty_provider_name() -> None:
    with pytest.raises(ValueError):
        ProviderSource(provider_name="", signal_reference="x")


def test_provider_source_rejects_empty_signal_reference() -> None:
    with pytest.raises(ValueError):
        ProviderSource(provider_name="x", signal_reference="")


def test_provider_source_immutable() -> None:
    ps = ProviderSource(provider_name="x", signal_reference="y")
    with pytest.raises(AttributeError):
        ps.provider_name = "z"


# --- SourceIdentity ---


def test_source_identity_valid() -> None:
    sid = SourceIdentity(source_type=SourceType.API)
    assert sid.source_type == SourceType.API
    assert sid.source_reference is None


def test_source_identity_rejects_invalid_source_type() -> None:
    with pytest.raises(TypeError):
        SourceIdentity(source_type="INVALID")


def test_source_identity_immutable() -> None:
    sid = SourceIdentity(source_type=SourceType.MANUAL)
    with pytest.raises(AttributeError):
        sid.source_type = SourceType.API


# --- Instrument ---


def test_instrument_valid() -> None:
    inst = Instrument(
        canonical_symbol="EURUSD",
        asset_class=AssetClass.FOREX,
    )
    assert inst.canonical_symbol == "EURUSD"
    assert inst.asset_class == AssetClass.FOREX


def test_instrument_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError):
        Instrument(canonical_symbol="", asset_class=AssetClass.FOREX)


def test_instrument_rejects_invalid_asset_class() -> None:
    with pytest.raises(TypeError):
        Instrument(canonical_symbol="X", asset_class="FOREX")


def test_instrument_immutable() -> None:
    inst = Instrument(canonical_symbol="BTCUSD", asset_class=AssetClass.CRYPTO)
    with pytest.raises(AttributeError):
        inst.canonical_symbol = "ETHUSD"
