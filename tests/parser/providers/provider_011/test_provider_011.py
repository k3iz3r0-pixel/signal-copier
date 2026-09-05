"""Provider 011 — lot/quantity family (INFERENCE).

Covered shapes:

1. lot numbers NEVER become ENTRY/SL/TP (false-positive axis); entry is
   the LAST number in the BEFORE_TOKEN SL zone;
2. integer and fractional lots; no-lots @ form;
3. two entry numbers → MALFORMED with both values preserved;
4. lots-only message → PARTIAL with entry_pending (quantity alone is not
   an entry);
5. chat prose → NO_SIGNAL; raw spans exact; determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ConflictKind, ParseResultState
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_011"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_011_fractional_lots_entry_is_price_not_quantity() -> None:
    r = _go("BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "0.5" in unbound


def test_provider_011_integer_lots() -> None:
    r = _go("SELL EURUSD 2 LOTS @ 1.2500 SL 1.2550 TP 1.2400")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.2500"))
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "2" in unbound


def test_provider_011_lot_never_in_price_slots() -> None:
    r = _go("BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100")
    by = _by_slot(r)
    for slot in (CandidateSlot.ENTRY, CandidateSlot.SL):
        assert by[slot] != Price(Decimal("0.5"))
    tp_values = {str(v) for v in by[CandidateSlot.TP]}
    assert "0.5" not in tp_values


def test_provider_011_double_entry_conflict_preserved() -> None:
    r = _go("BUY EURUSD 0.5 LOTS @ 1.1000 1.1010 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.ENTRY].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[CandidateSlot.ENTRY].involved} == {
        Price(Decimal("1.1000")),
        Price(Decimal("1.1010")),
    }
    by = _by_slot(r)
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))


def test_provider_011_no_lots_at_form() -> None:
    r = _go("BUY EURUSD @ 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))


def test_provider_011_lots_only_partial() -> None:
    r = _go("BUY EURUSD 0.5 LOTS")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "0.5" in unbound
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence}
    assert "entry_pending" in kinds


def test_provider_011_chat_text_no_signal() -> None:
    assert _go("lots of talk, zero signals").outcome is ParseResultState.NO_SIGNAL


def test_provider_011_raw_source_spans_are_exact() -> None:
    text = "BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100"
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_011_deterministic() -> None:
    text = "BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_011_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.sl.number" in ids and "common.tp.number" in ids
    assert "p011.entry.last_before_sl" in ids
    assert ids and all(rule_id.startswith(("p011.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
