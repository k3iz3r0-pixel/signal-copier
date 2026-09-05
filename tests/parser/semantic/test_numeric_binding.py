"""Numeric semantic binding regression tests (Phase 2B.1 remediation).

The Phase 2B architecture audit verified false positives where numeric
tokens were bound to ENTRY/SL/TP based on positional proximity alone:

- "BUY EURUSD SL 1.0950 TP 1.1100"  -> SL number bound as ENTRY
- "BUY EURUSD 2026-09-05"           -> date numbers bound as ENTRY
- phone digits after a valid signal -> digits bound as TP
- "BUY EURUSD risk 2% 1.1000 ..."   -> percentage bound as ENTRY

The generic semantic binding architecture requires a number to be
AUTHORIZED before it can bind to a field:

- field values bind only inside their anchor's BOUNDED value zone;
- a number is claimed by exactly one semantic field (explicit anchored
  fields and action/condition captures claim their values; keyword-less
  whole-message rules bind only unclaimed, core-adjacent numbers);
- percent-suffixed numbers and members of >=3-number punctuation chains
  (dates, thousands separators) are never prices.

These tests prove the GENERIC behavior with fresh message shapes — none of
them repeats a profile rule; if a profile rule were tuned to one example,
the sibling cases would still hold.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_001"


def _go(text: str, provider: str = PROVIDER):
    return parse(make_raw(text), make_metadata(provider), make_runtime(provider))


def _prices(result) -> set[str]:
    return {str(c.value) for c in result.ir.candidates if c.slot is CandidateSlot.PRICE}


# ---------------------------------------------------------------------------
# SL value must not become ENTRY when no entry number exists
# ---------------------------------------------------------------------------


def test_sl_number_is_not_bound_as_entry() -> None:
    r = _go("BUY EURUSD SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARTIAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value is None for f in entry_fragments)
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    # The number is preserved as an unbound PRICE candidate for audit.
    assert "1.0950" in _prices(r)


def test_entry_fallback_requires_an_unclaimed_number_generic() -> None:
    """Sibling shape: SL-anchored number without TP — still no fake ENTRY."""
    r = _go("SELL GBPUSD SL 1.2550")
    assert r.outcome is ParseResultState.PARTIAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value is None for f in entry_fragments)
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.SL] == Price(Decimal("1.2550"))


def test_second_anchor_sl_value_not_stolen_by_entry_zone() -> None:
    """TP placed before SL must not turn the SL value into an ENTRY, and
    the TP zone must stop before the SL field."""
    r = _go("BUY EURUSD 1.1000 TP 1.1100 SL 1.0950")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    assert by_slot[CandidateSlot.SL] == Price(Decimal("1.0950"))


# ---------------------------------------------------------------------------
# Date-like numeric chains are not prices
# ---------------------------------------------------------------------------


def test_date_numbers_are_not_bound_as_entry() -> None:
    r = _go("BUY EURUSD 2026-09-05")
    assert r.outcome is ParseResultState.PARTIAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value is None for f in entry_fragments)
    geometry = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY_GEOMETRY]
    assert all(f.value is None for f in geometry)
    # The date components are preserved as unbound PRICE candidates.
    assert {"2026", "9", "5"} <= _prices(r)


def test_date_after_direction_and_symbol_sell_variant() -> None:
    """Fresh shape: the chain rule is structural, not example-specific."""
    r = _go("SELL EURUSD 2026-09-05 done")
    assert r.outcome is ParseResultState.PARTIAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value is None for f in entry_fragments)


def test_date_numbers_do_not_form_a_price_range() -> None:
    """A 3-number dash chain must not produce a PriceRange ENTRY either."""
    r = _go("BUY XAUUSD 2026-09-05 SL 2340 TP 2400")
    entries = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(not isinstance(f.value, tuple) or len(f.value) == 0 for f in entries)
    for fragment in entries:
        assert not hasattr(fragment.value, "low")


def test_two_number_range_still_parses() -> None:
    """A 2-number dash chain remains a legitimate price range."""
    r = _go("BUY XAUUSD 2350-2360 SL 2340 TP 2400")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY].low == Price(Decimal(2350))
    assert by_slot[CandidateSlot.ENTRY].high == Price(Decimal(2360))


def test_thousands_separated_number_is_not_a_price() -> None:
    """'1,100,000' is a chain of three numbers — not three prices."""
    r = _go("BUY EURUSD 1,100,000 SL 1.0900")
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value is None for f in entry_fragments)


# ---------------------------------------------------------------------------
# Trailing content must not be absorbed into field value zones
# ---------------------------------------------------------------------------


def test_phone_digits_after_signal_are_not_tp() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 contact +441234567890")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    # The phone digits remain preserved as an unbound PRICE candidate.
    assert "441234567890" in _prices(r)


def test_phone_digits_directly_after_tp_value_are_not_tp() -> None:
    """Fresh shape: no prose word, generic punctuation breaks the zone."""
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 +998877665544")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    assert "998877665544" in _prices(r)


def test_multi_value_separator_tp_list_still_binds() -> None:
    """Declared multi-value separators remain inside the value zone."""
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100/1.1150")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.TP] == (
        Price(Decimal("1.1100")),
        Price(Decimal("1.1150")),
    )


# ---------------------------------------------------------------------------
# Percentages are never prices
# ---------------------------------------------------------------------------


def test_risk_percent_is_not_entry_and_entry_still_binds() -> None:
    r = _go("BUY EURUSD risk 2% 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    # The percentage number is preserved as an unbound PRICE candidate.
    assert "2" in _prices(r)


def test_percent_number_without_prose_is_not_entry() -> None:
    """Fresh shape: no prose word at all — the percent form still loses."""
    r = _go("BUY EURUSD 2% 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert "2" in _prices(r)


def test_percent_number_is_not_sl() -> None:
    """A percent value in an SL zone is not a stop loss."""
    r = _go("BUY EURUSD 1.1000 SL 50% TP 1.1100")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert CandidateSlot.SL not in by_slot
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert "50" in _prices(r)


# ---------------------------------------------------------------------------
# Legit signals must keep parsing (no over-correction)
# ---------------------------------------------------------------------------


def test_canonical_signal_still_parses() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by_slot[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_laddered_entries_still_parse_as_multiple() -> None:
    r = _go("BUY EURUSD 1.1000 1.1050 SL 1.0950")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == (
        Price(Decimal("1.1000")),
        Price(Decimal("1.1050")),
    )
    assert by_slot[CandidateSlot.ENTRY_GEOMETRY].name == "MULTIPLE"


def test_condition_at_price_and_entry_coexist() -> None:
    """An AT-condition capture does not erase the entry binding."""
    r = _go("BUY EURUSD AT 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert any(f.slot is CandidateSlot.CONDITION for f in r.ir.fragments)


def test_provider_003_no_entry_falls_back_to_partial() -> None:
    """provider_003's whole-message entry rule binds only unclaimed numbers."""
    r = _go("LONG BTC SL 58000 TP 65000", provider="provider_003")
    assert r.outcome is ParseResultState.PARTIAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value is None for f in entry_fragments)
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.SL] == Price(Decimal(58000))
    assert by_slot[CandidateSlot.TP] == (Price(Decimal(65000)),)


def test_provider_003_real_entry_still_binds() -> None:
    r = _go("LONG BTC 60000 SL 58000 TP 65000", provider="provider_003")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal(60000))
