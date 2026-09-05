"""Provider 004 — emoji field markers, line-structured (design §21.4).

Covered shapes:

1. canonical emoji-marker lines (🎯 / 🛑 / 💰) with hashtag symbol header;
2. multi-TP via repeated 💰 lines;
3. LINE-scope containment (marker cannot capture across lines);
4. percent false-positive protection ("🛑 2%" is never a price);
5. conflicting entry markers preserved → MALFORMED;
6. action flow + no-signal chat text + determinism + isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    ConflictKind,
    MessageEvent,
    ParseResultState,
)
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_004"

GREEN = "\U0001f7e2"
RED = "\U0001f534"
ENTRY_MARK = "\U0001f3af"
SL_MARK = "\U0001f6d1"
TP_MARK = "\U0001f4b0"


def _go(text: str, event: MessageEvent = MessageEvent.CREATE):
    return parse(make_raw(text), make_metadata(PROVIDER, event), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_004_canonical_buy_parses() -> None:
    text = (
        f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\n{SL_MARK} 1.0950\n{TP_MARK} 1.1100"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    assert by[CandidateSlot.ENTRY_GEOMETRY].name == "SINGLE"


def test_provider_004_sell_two_tp_levels() -> None:
    text = f"{RED} SELL #EURUSD\n{ENTRY_MARK} 1.2500\n{SL_MARK} 1.2550\n{TP_MARK} 1.2400\n{TP_MARK} 1.2350"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.TP] == (
        Price(Decimal("1.2400")),
        Price(Decimal("1.2350")),
    )


def test_provider_004_marker_cannot_capture_across_lines() -> None:
    """LINE scope: an entry marker line must not capture the next line's
    number, and a number on a marker-less line is never bound as ENTRY."""
    text = (
        f"{GREEN} BUY #EURUSD\n{ENTRY_MARK}\n1.1000\n{SL_MARK} 1.0950\n{TP_MARK} 1.1100"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))


def test_provider_004_conflicting_entry_markers_malformed() -> None:
    text = f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\n{ENTRY_MARK} 1.1050\n{SL_MARK} 1.0950\n{TP_MARK} 1.1100"
    r = _go(text)
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c.kind for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.ENTRY] is ConflictKind.CONFLICTING
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"


def test_provider_004_percent_sl_never_becomes_price() -> None:
    text = f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\n{SL_MARK} 2%\n{TP_MARK} 1.1100"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert CandidateSlot.SL not in by
    price_values = {str(c.value) for c in r.ir.candidates if c.slot.name == "PRICE"}
    assert "2" in price_values


def test_provider_004_keyword_sl_mixed_with_markers() -> None:
    """Common SL/TP keyword rules stay available next to the emoji form."""
    text = f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\nSL 1.0950\n{TP_MARK} 1.1100"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    assert _by_slot(r)[CandidateSlot.SL] == Price(Decimal("1.0950"))


def test_provider_004_action_close_half() -> None:
    text = f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\nCLOSE HALF"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions and actions[0].value.name == "PARTIAL_CLOSE"


def test_provider_004_chat_text_no_signal() -> None:
    r = _go(f"hello {GREEN} world, party \U0001f389 time")
    assert r.outcome is ParseResultState.NO_SIGNAL
    assert _go("").outcome is ParseResultState.NO_SIGNAL


def test_provider_004_raw_source_spans_are_exact() -> None:
    text = (
        f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\n{SL_MARK} 1.0950\n{TP_MARK} 1.1100"
    )
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot.name == "PRICE"]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_004_deterministic() -> None:
    text = (
        f"{GREEN} BUY #EURUSD\n{ENTRY_MARK} 1.1000\n{SL_MARK} 1.0950\n{TP_MARK} 1.1100"
    )
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_004_profile_isolation() -> None:
    """provider_004's runtime contains no foreign provider rules and does
    not mutate the shared registry."""
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert ids and all(rule_id.startswith(("p004.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
