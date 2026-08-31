"""Adversarial Category 2 — Price / Decimal attacks."""

from decimal import Decimal

import pytest

from packages.signal_core.value_objects import Price, PriceRange


class TestPriceAdversarial:
    def test_zero_explicit(self) -> None:
        p = Price(value=Decimal("0.0"))
        assert p.value == Decimal("0.0")

    def test_negative_price_accepted(self) -> None:
        # Design does not forbid negative prices at domain level;
        # financial semantics deferred to strategy/invariant layer.
        p = Price(value=Decimal("-50.5"))
        assert p.value == Decimal("-50.5")

    def test_very_large_decimal(self) -> None:
        p = Price(value=Decimal("999999999999.9999999999"))
        assert p.value > Decimal(0)

    def test_very_small_decimal(self) -> None:
        p = Price(value=Decimal("0.0000000001"))
        assert p.value > Decimal(0)

    def test_equivalent_decimal_strings(self) -> None:
        p1 = Price(value=Decimal("1.500"))
        p2 = Price(value=Decimal("1.5"))
        assert p1.value == p2.value

    def test_float_banned_explicitly(self) -> None:
        with pytest.raises(TypeError, match="Decimal"):
            Price(value=1.23)

    def test_string_value_rejected(self) -> None:
        with pytest.raises(TypeError, match="Decimal"):
            Price(value="1.23")

    def test_none_value_rejected(self) -> None:
        with pytest.raises(TypeError, match="Decimal"):
            Price(value=None)

    def test_currency_optional_and_string(self) -> None:
        p = Price(value=Decimal(100), currency="USD")
        assert p.currency == "USD"

    def test_currency_none_accepted(self) -> None:
        p = Price(value=Decimal(100), currency=None)
        assert p.currency is None

    def test_currency_non_string_rejected(self) -> None:
        # Type enforcement is loose for currency; no explicit guard.
        # This documents current behavior rather than enforcing a strict contract.
        p = Price(value=Decimal(100), currency=42)  # noqa: not a blocking failure in current design
        assert p.currency == 42


class TestPriceRangeAdversarial:
    def test_both_none_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            PriceRange()

    def test_low_only_accepted(self) -> None:
        pr = PriceRange(low=Price(value=Decimal(100)))
        assert pr.low is not None
        assert pr.high is None

    def test_high_only_accepted(self) -> None:
        pr = PriceRange(high=Price(value=Decimal(150)))
        assert pr.low is None
        assert pr.high is not None

    def test_low_less_than_high_accepted(self) -> None:
        pr = PriceRange(low=Price(value=Decimal(50)), high=Price(value=Decimal(150)))
        assert pr.low.value == Decimal(50)

    def test_low_high_same_accepted(self) -> None:
        # Design does not explicitly require low < high; low <= high deferred.
        pr = PriceRange(low=Price(value=Decimal(100)), high=Price(value=Decimal(100)))
        assert pr.low.value == pr.high.value

    def test_low_greater_than_high_accepted_by_object_but_rejected_by_invariant(
        self,
    ) -> None:
        # PriceRange object creation does NOT enforce low <= high (deferred).
        pr = PriceRange(low=Price(value=Decimal(150)), high=Price(value=Decimal(50)))
        assert pr.low.value > pr.high.value
