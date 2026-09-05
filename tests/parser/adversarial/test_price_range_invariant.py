"""PriceRange invariant (Phase 2D item 1) — low <= high, enforced.

Regression coverage for §5.6 range binding:

1. ascending (low < high) ranges stay valid and bind as PriceRange with
   RANGE geometry;
2. degenerate (low == high) ranges stay valid (existing behavior);
3. inverted (low > high) ranges must NEVER bind — no PriceRange value
   anywhere in fragments or candidates, no RANGE geometry; the endpoint
   numbers stay preserved PRICE candidates;
4. malformed range syntax (≥3-number chain, dangling separator) never
   forms a range;
5. provider range normalization: which separators form ranges is
   profile-driven (range_patterns), never hardcoded;
6. deterministic outcomes (double parse equality).
"""

from __future__ import annotations

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.value_objects import PriceRange
from tests.parser._helpers import make_metadata, make_raw, make_runtime


def _go(provider: str, text: str):
    return parse(make_raw(text), make_metadata(provider), make_runtime(provider))


def _entry(result):
    return next(
        (f.value for f in result.ir.fragments if f.slot is CandidateSlot.ENTRY), None
    )


def _geometry(result):
    return next(
        (
            f.value
            for f in result.ir.fragments
            if f.slot is CandidateSlot.ENTRY_GEOMETRY
        ),
        None,
    )


def _range_values(result) -> set[PriceRange]:
    values: set[PriceRange] = set()
    for fragment in result.ir.fragments:
        value = fragment.value
        candidates = value if isinstance(value, tuple) else (value,)
        for item in candidates:
            if isinstance(item, PriceRange):
                values.add(item)
    for candidate in result.ir.candidates:
        if isinstance(candidate.value, PriceRange):
            values.add(candidate.value)
    return values


def test_ascending_range_valid() -> None:
    r = _go("provider_014", "BUY EURUSD 4267/4270\nSL 4257")
    assert r.outcome is ParseResultState.PARSED
    entry = _entry(r)
    assert isinstance(entry, PriceRange)
    assert entry.low is not None and entry.high is not None
    assert entry.low.value <= entry.high.value
    assert _geometry(r) is not None and _geometry(r).name == "RANGE"


def test_degenerate_range_low_eq_high_valid() -> None:
    r = _go("provider_014", "BUY EURUSD 100/100\nSL 99")
    assert r.outcome is ParseResultState.PARSED
    entry = _entry(r)
    assert isinstance(entry, PriceRange)
    assert entry.low.value == entry.high.value


def test_inverted_range_never_binds() -> None:
    r = _go("provider_014", "BUY EURUSD 300/250\nSL 280")
    assert _range_values(r) == set()
    geometry = _geometry(r)
    assert geometry is None or geometry.name != "RANGE"
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "300" in unbound and "250" in unbound


def test_inverted_range_under_provider_001_never_binds() -> None:
    r = _go("provider_001", "BUY EURUSD 300-250\nSL 280")
    assert _range_values(r) == set()
    geometry = _geometry(r)
    assert geometry is None or geometry.name != "RANGE"


def test_three_number_chain_never_range() -> None:
    r = _go("provider_014", "BUY EURUSD 4267-4270-4280\nSL 4257")
    assert _range_values(r) == set()
    assert _geometry(r) is None or _geometry(r).name != "RANGE"


def test_dangling_separator_never_range() -> None:
    r = _go("provider_014", "BUY EURUSD 4267/\nSL 4257")
    assert _range_values(r) == set()
    assert _geometry(r) is None or _geometry(r).name != "RANGE"


def test_range_normalization_is_provider_driven() -> None:
    text = "BUY EURUSD 4267/4270\nSL 4257"
    wide = _go("provider_014", text)
    narrow = _go("provider_001", text)
    wide_entry = _entry(wide)
    narrow_geometry = _geometry(narrow)
    assert isinstance(wide_entry, PriceRange)
    assert narrow_geometry is None or narrow_geometry.name != "RANGE"


def test_range_outcomes_deterministic() -> None:
    for provider, text in (
        ("provider_014", "BUY EURUSD 4267/4270\nSL 4257"),
        ("provider_014", "BUY EURUSD 300/250\nSL 280"),
        ("provider_001", "BUY EURUSD 300-250\nSL 280"),
    ):
        first = _go(provider, text)
        second = _go(provider, text)
        assert (first.outcome, first.ir) == (second.outcome, second.ir)
