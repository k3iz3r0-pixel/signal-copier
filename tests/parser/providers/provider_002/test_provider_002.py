"""Provider 002 — multiline, em-dash field separators (design §21.2).

Three structurally different shapes for this provider:

1. canonical multi-line (BUY EURUSD \n ENTRY 1.1000 \n SL — 1.0950 \n TP — 1.1100);
2. em-dash separator override mechanism (renamed masking overrides
   ``common.sl.number`` and ``common.tp.number``);
3. unicode variation — providers using fullwidth punctuation also normalize.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    ParseResultState,
)
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_002"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def test_provider_002_multiline_signal_parses() -> None:
    text = "BUY EURUSD\nENTRY 1.1000\nSL — 1.0950\nTP — 1.1100"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by_slot[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by_slot[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_provider_002_sell_signal_parses() -> None:
    text = "SELL GBPJPY\nENTRY 150.00\nSL — 151.00\nTP — 148.00"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by_slot[CandidateSlot.INSTRUMENT] == "GBPJPY"


def test_provider_002_emdash_normalized_to_canonical() -> None:
    """The em-dash character survives as a single separator character
    (canonical_separator_canonicalization), but the em-dash SL/TP regex rules
    still match."""
    text = "BUY EURUSD\nENTRY 1.1000\nSL \u2014 1.0950\nTP \u2014 1.1100"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED


def test_provider_002_overrides_mask_common_rules() -> None:
    """The em-dash SL/TP rules override the common SL/TP rules via renamed
    overrides (§12.5.7); the common keyword-based SL/TP rules are absent
    from the effective rule set."""
    rt = make_runtime(PROVIDER)
    rule_ids = {r.id for r in rt.effective_rules}
    assert "p002.sl.emdash" in rule_ids
    assert "p002.tp.emdash" in rule_ids
    # The common SL/TP rules were masked by overrides (not re-declared).
    # resolve_effective_rule_sets should have removed them.
    assert "common.sl.number" not in rule_ids
    assert "common.tp.number" not in rule_ids


def test_provider_002_action_close_half() -> None:
    text = "BUY EURUSD\nENTRY 1.1000\nSL — 1.0950\nTP — 1.1100\nCLOSE HALF"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert any(a.value.name == "PARTIAL_CLOSE" for a in actions)


def test_provider_002_direction_only_partial() -> None:
    r = _go("BUY")
    assert r.outcome is ParseResultState.PARTIAL