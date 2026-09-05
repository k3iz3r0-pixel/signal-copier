"""Provider 008 — colon key-value field tables (INFERENCE family).

Covered shapes:

1. canonical pipe tables (single line and one pair per line);
2. declared `:`/`|` separators make value zones bind (glue, §7.4);
3. duplicate `Entry:` → MALFORMED with both values preserved;
4. missing entry → PARTIAL with entry_pending;
5. signal+action message keeps signal fragments (keyword-declared
   overrides tolerate action context);
6. reference numbers never bind; chat prose → NO_SIGNAL;
7. raw span exactness; determinism; profile isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ConflictKind, ParseResultState
from packages.signal_core.enums import InstructionType, TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_008"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_008_buy_pipe_table() -> None:
    r = _go("Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | TP: 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_provider_008_sell_line_per_field() -> None:
    r = _go("Pair: EURUSD\nSide: SELL\nEntry: 1.2500\nSL: 1.2550\nTP: 1.2400")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.2500"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.2550"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.2400")),)


def test_provider_008_duplicate_entry_conflict() -> None:
    r = _go(
        "Pair: EURUSD | Side: BUY | Entry: 1.1000 | Entry: 1.1050 | "
        "SL: 1.0950 | TP: 1.1100"
    )
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.ENTRY].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[CandidateSlot.ENTRY].involved} == {
        Price(Decimal("1.1000")),
        Price(Decimal("1.1050")),
    }


def test_provider_008_missing_entry_partial() -> None:
    r = _go("Pair: EURUSD | Side: BUY | SL: 1.0950 | TP: 1.1100")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence}
    assert "entry_pending" in kinds


def test_provider_008_signal_plus_action_keeps_signal_fragments() -> None:
    r = _go(
        "Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | "
        "TP: 1.1100 | CLOSE HALF"
    )
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    assert by[CandidateSlot.ACTION] is InstructionType.PARTIAL_CLOSE


def test_provider_008_reference_number_never_binds() -> None:
    r = _go(
        "Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | "
        "TP: 1.1100 | Ref: 90210"
    )
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "90210" in unbound


def test_provider_008_chat_text_no_signal() -> None:
    assert _go("some random chat about pairs and sides").outcome is (
        ParseResultState.NO_SIGNAL
    )


def test_provider_008_raw_source_spans_are_exact() -> None:
    text = "Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | TP: 1.1100"
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_008_deterministic() -> None:
    text = "Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | TP: 1.1100"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_008_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.sl.number" not in ids
    assert "p008.sl.colon" in ids
    assert ids and all(rule_id.startswith(("p008.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
