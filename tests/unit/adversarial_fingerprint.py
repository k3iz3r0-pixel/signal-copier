"""Adversarial Category 8 — Fingerprint / canonicalization attacks."""

from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import canonical_fingerprint
from packages.signal_core.enums import AssetClass, SignalStatus, TradeDirection
from packages.signal_core.value_objects import Instrument, Price, PriceRange


class TestFingerprintCanonicalization:
    # --- Basic types ---
    def test_str_normalization_deterministic(self) -> None:
        fp = canonical_fingerprint((("k", "hello"),))
        assert isinstance(fp, str) and len(fp) == 64

    def test_int_normalization(self) -> None:
        fp = canonical_fingerprint((("k", 42),))
        assert isinstance(fp, str) and len(fp) == 64

    def test_bool_true_false_distinct_fingerprint(self) -> None:
        fp_true = canonical_fingerprint((("v", True),))
        fp_false = canonical_fingerprint((("v", False),))
        assert fp_true != fp_false

    def test_none_value(self) -> None:
        fp = canonical_fingerprint((("v", None),))
        assert isinstance(fp, str) and len(fp) == 64

    def test_decimal_equivalent_strings_same_fingerprint(self) -> None:
        fp1 = canonical_fingerprint((("p", Decimal("10.5")),))
        fp2 = canonical_fingerprint((("p", Decimal("10.500")),))
        assert fp1 == fp2

    def test_decimal_different_value_different_fingerprint(self) -> None:
        fp1 = canonical_fingerprint((("p", Decimal("10.5")),))
        fp2 = canonical_fingerprint((("p", Decimal("10.5001")),))
        assert fp1 != fp2

    def test_uuid_string_normalization(self) -> None:
        u = uuid4()
        fp = canonical_fingerprint((("ref", u),))
        assert isinstance(fp, str) and len(fp) == 64
        # UUID should be normalized as string, not a UUID object in JSON

    def test_enum_normalization(self) -> None:
        fp = canonical_fingerprint((("dir", TradeDirection.BUY),))
        assert isinstance(fp, str) and len(fp) == 64

    # --- Domain value objects ---
    def test_price_object_normalization(self) -> None:
        fp = canonical_fingerprint((("price", Price(value=Decimal("99.99"))),))
        assert isinstance(fp, str) and len(fp) == 64

    def test_price_range_object_normalization(self) -> None:
        fp = canonical_fingerprint(
            (
                (
                    "range",
                    PriceRange(
                        low=Price(value=Decimal(50)), high=Price(value=Decimal(150))
                    ),
                ),
            )
        )
        assert isinstance(fp, str) and len(fp) == 64

    def test_instrument_object_normalization(self) -> None:
        fp = canonical_fingerprint(
            (
                (
                    "inst",
                    Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
                ),
            )
        )
        assert isinstance(fp, str) and len(fp) == 64

    # --- Key ordering independence ---
    def test_key_reordering_same_fingerprint(self) -> None:
        fp1 = canonical_fingerprint((("b", 2), ("a", 1)))
        fp2 = canonical_fingerprint((("a", 1), ("b", 2)))
        assert fp1 == fp2

    # --- Tuple ordering semantic (must differ) ---
    def test_tuple_ordering_changes_fingerprint(self) -> None:
        fp1 = canonical_fingerprint((("levels", (1, 2, 3)),))
        fp2 = canonical_fingerprint((("levels", (3, 2, 1)),))
        assert fp1 != fp2

    # --- Nested tuple support ---
    def test_nested_tuple_price(self) -> None:
        fp = canonical_fingerprint(
            (("nested", (Price(value=Decimal(10)), Price(value=Decimal(20)))),)
        )
        assert isinstance(fp, str) and len(fp) == 64

    def test_nested_tuple_decimal(self) -> None:
        fp = canonical_fingerprint((("nested", (Decimal("5.5"), Decimal("6.6"))),))
        assert isinstance(fp, str) and len(fp) == 64

    def test_nested_tuple_uuid(self) -> None:
        fp = canonical_fingerprint((("nested", (uuid4(), uuid4())),))
        assert isinstance(fp, str) and len(fp) == 64

    # --- Unsupported nested rejection ---
    def test_nested_dict_rejected_by_fingerprint(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            canonical_fingerprint((("bad", {"nested": True}),))

    def test_nested_list_rejected_by_fingerprint(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            canonical_fingerprint((("bad", [1, 2, 3]),))

    def test_nested_set_rejected_by_fingerprint(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            canonical_fingerprint((("bad", {1, 2}),))

    def test_nested_custom_object_rejected_by_fingerprint(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            canonical_fingerprint((("bad", object()),))

    # --- Empty / edge cases ---
    def test_empty_snapshot_fingerprint_stable(self) -> None:
        fp1 = canonical_fingerprint(())
        fp2 = canonical_fingerprint(())
        assert fp1 == fp2
        assert isinstance(fp1, str)
        assert len(fp1) == 64

    def test_unicode_string_fingerprint(self) -> None:
        fp = canonical_fingerprint((("text", "日本語テスト"),))
        assert isinstance(fp, str) and len(fp) == 64

    def test_booleans_distinct_fingerprint(self) -> None:
        fp_true = canonical_fingerprint((("x", True),))
        fp_false = canonical_fingerprint((("x", False),))
        assert fp_true != fp_false

    def test_none_value_fingerprint(self) -> None:
        fp = canonical_fingerprint((("null", None),))
        assert isinstance(fp, str) and len(fp) == 64

    # --- Metadata independence ---
    def test_metadata_changes_do_not_change_fingerprint_for_same_snapshot(self) -> None:
        snapshot = (("status", SignalStatus.ACTIVE),)
        fp = canonical_fingerprint(snapshot)
        assert fp == canonical_fingerprint(snapshot)

    # --- Float explicitly excluded ---
    def test_float_rejected_by_fingerprint(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            canonical_fingerprint((("bad", 3.14),))
