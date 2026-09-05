"""Provider 010 — unusual field ordering (INFERENCE family).

Covered shapes:

1. SL/TP before entry, TP-first, and no-TP forms all bind identically
   (order independence of bounded zones + core adjacency);
2. symbol-last form stays PARTIAL with the entry value preserved (§5.6
   no-guessing);
3. direction conflicts preserved → MALFORMED;
4. chat prose → NO_SIGNAL; raw spans exact; determinism; isolation
   (profile inherits common rules unchanged).
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ConflictKind, ParseResultState
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_010"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_010_sl_tp_before_entry() -> None:
    r = _go("BUY SL 1.0950 TP 1.1100 EURUSD 1.1000")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_provider_010_tp_first_ordering() -> None:
    r = _go("TP 1.2400 SELL EURUSD 1.2500 SL 1.2550")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.TP] == (Price(Decimal("1.2400")),)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.2500"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.2550"))


def test_provider_010_ordering_never_cross_contaminates() -> None:
    """SL zone stops at the TP keyword; TP zone stops at the symbol."""
    r = _go("BUY SL 1.0950 TP 1.1100 EURUSD 1.1000")
    by = _by_slot(r)
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))


def test_provider_010_symbol_last_partial_no_guessing() -> None:
    r = _go("BUY 1.1000 SL 1.0950 TP 1.1100 EURUSD")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "1.1000" in unbound
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence}
    assert "entry_pending" in kinds


def test_provider_010_no_tp_form() -> None:
    r = _go("BUY SL 1.0950 EURUSD 1.1000")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))


def test_provider_010_direction_conflict_malformed() -> None:
    r = _go("SELL SL 1.0950 TP 1.1100 EURUSD 1.1000 BUY")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.DIRECTION].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[CandidateSlot.DIRECTION].involved} == {
        TradeDirection.SELL,
        TradeDirection.BUY,
    }


def test_provider_010_chat_text_no_signal() -> None:
    assert _go("sl tp entry — random ordering talk").outcome is (
        ParseResultState.NO_SIGNAL
    )


def test_provider_010_raw_source_spans_are_exact() -> None:
    text = "BUY SL 1.0950 TP 1.1100 EURUSD 1.1000"
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_010_deterministic() -> None:
    text = "BUY SL 1.0950 TP 1.1100 EURUSD 1.1000"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_010_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.sl.number" in ids and "common.tp.number" in ids
    assert ids and all(rule_id.startswith(("p010.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
