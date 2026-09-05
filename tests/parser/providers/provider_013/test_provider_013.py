"""Provider 013 — real bracket-annotated ticket-block family.

Evidence: docs/corpus/real-messages.md M1-M4 (verbatim fixtures).

Covered:

1. M2 NEW-SIGNAL block parses with annotations (lots/pips/RR/ticket)
   never bound (false-positive axis);
2. M1 closed-event and M3 weekly report stay NO_SIGNAL (NEW-header
   gating on REGEX rules; direction/entry keywords suppressed);
3. M4 action: MOVE_SL with the new level; Old SL never bound (FORBIDS);
   no SL fragment, no SL conflict;
4. report-like direction/instrument-only prose stays NO_SIGNAL;
5. raw spans exact; determinism; profile isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.enums import InstructionType, TradeDirection
from packages.signal_core.value_objects import Price
from tests.fixtures.providers.provider_013.canonical import EXAMPLES
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_013"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def _m(name: str) -> str:
    return next(e["raw_text"] for e in EXAMPLES if e["name"] == name)


def test_013_m2_signal_full_fields() -> None:
    r = _go(_m("m2_new_order_signal"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.INSTRUMENT] == "XAUUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("2656.00"))
    assert by[CandidateSlot.SL] == Price(Decimal("2659.99"))
    assert by[CandidateSlot.TP] == (Price(Decimal("2647.79")),)
    assert by[CandidateSlot.ENTRY_GEOMETRY] is not None


def test_013_m2_annotations_never_bind() -> None:
    r = _go(_m("m2_new_order_signal"))
    bound_values = {str(f.value) for f in r.ir.fragments}
    for annotation in ("2.50", "39.9", "82.1", "2.06", "508432522"):
        assert annotation not in bound_values
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    for annotation in ("2.50", "39.9", "82.1", "2.06", "508432522"):
        assert annotation in unbound


def test_013_m1_closed_event_no_signal() -> None:
    r = _go(_m("m1_closed_event"))
    assert r.outcome is ParseResultState.NO_SIGNAL
    assert _by_slot(r).get(CandidateSlot.DIRECTION) is None
    assert _by_slot(r).get(CandidateSlot.ENTRY) is None


def test_013_m3_weekly_report_no_signal() -> None:
    r = _go(_m("m3_weekly_report"))
    assert r.outcome is ParseResultState.NO_SIGNAL
    by = _by_slot(r)
    assert by.get(CandidateSlot.DIRECTION) is None
    assert by.get(CandidateSlot.ENTRY) is None
    percentages = {
        str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE
    }
    assert "1.7" in percentages


def test_013_m4_move_sl_action() -> None:
    r = _go(_m("m4_moved_sl_action"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL
    assert by[CandidateSlot.INSTRUMENT] == "XAUUSD"
    action_frags = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    snippets = [e.snippet for f in action_frags for e in f.evidence if e.snippet]
    assert "2726.94" in snippets


def test_013_m4_old_sl_never_bound() -> None:
    r = _go(_m("m4_moved_sl_action"))
    by = _by_slot(r)
    assert by.get(CandidateSlot.SL) is None
    assert r.ir.conflicts == ()
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "2723.94" in unbound and "2726.94" in unbound


def test_013_no_new_marker_prose_stays_no_signal() -> None:
    assert (
        _go("XAUUSD Sell around current levels").outcome is ParseResultState.NO_SIGNAL
    )


def test_013_signal_without_new_header_not_parsed() -> None:
    r = _go("XAUUSD Sell\nEntry: 2656.00\nSL: 2659.99\nTP: 2647.79")
    assert r.outcome is ParseResultState.NO_SIGNAL


def test_013_raw_source_spans_are_exact() -> None:
    text = _m("m2_new_order_signal")
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_013_deterministic() -> None:
    text = _m("m2_new_order_signal")
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_013_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "p013.direction" in ids and "p013.sl" in ids
    assert "common.action.move_sl" in ids
    assert ids and all(rule_id.startswith(("p013.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
