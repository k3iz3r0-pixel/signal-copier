"""Provider 015 — real labeled scalp-card family (ForexGran/FXG).

Evidence: docs/corpus/real-messages.md M7, M8 (verbatim fixtures).

Covered:

1. canonical cards: Pair/Direction labels, past-tense entry prose
   (BOUGHT/SOLD canonical), at-entry, SL, ordinal TP1/TP2/TP3 in order;
2. Long+BOUGHT same-value direction dedupe (single BUY fragment);
3. dense noise never binds: accuracy ±78%, position-size 2%, lot sizes
   (100 / 21.28), R-multiples and pip annotations, ticket numbers;
4. both directions and both entry verbs; raw spans exact; determinism;
   isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.fixtures.providers.provider_015.canonical import EXAMPLES
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_015"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def _m(name: str) -> str:
    return next(e["raw_text"] for e in EXAMPLES if e["name"] == name)


def test_015_m7_canonical_card() -> None:
    r = _go(_m("m7_bought_long_card"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.16122"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.16112"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal("1.16132")),
        Price(Decimal("1.16147")),
        Price(Decimal("1.16172")),
    )


def test_015_m8_sell_card() -> None:
    r = _go(_m("m8_sold_short_card"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.16186"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.16233"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal("1.16153")),
        Price(Decimal("1.16068")),
        Price(Decimal("1.15951")),
    )


def test_015_direction_dedupe_single_fragment() -> None:
    r = _go(_m("m7_bought_long_card"))
    direction_frags = [f for f in r.ir.fragments if f.slot is CandidateSlot.DIRECTION]
    assert len(direction_frags) == 1
    assert r.ir.conflicts == ()


def test_015_noise_never_binds() -> None:
    r = _go(_m("m7_bought_long_card"))
    bound = {str(f.value) for f in r.ir.fragments}
    for noise in ("78", "2", "1.0", "100", "300"):
        assert noise not in bound
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    for noise in ("78", "2", "1.0", "100", "300"):
        assert noise in unbound


def test_015_r_multiples_never_bind() -> None:
    for name in ("m7_bought_long_card", "m8_sold_short_card"):
        r = _go(_m(name))
        bound = {str(f.value) for f in r.ir.fragments}
        for r_multiple in ("1", "2.5", "5", "0.7"):
            assert r_multiple not in bound


def test_015_prose_only_no_signal() -> None:
    assert _go("we are watching this pair today").outcome is ParseResultState.NO_SIGNAL


def test_015_raw_source_spans_are_exact() -> None:
    text = _m("m7_bought_long_card")
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_015_deterministic() -> None:
    text = _m("m7_bought_long_card")
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_015_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.sl.number" not in ids and "common.tp.number" not in ids
    assert "common.condition.at_price" not in ids
    assert "p015.entry.at" in ids and "p015.tp.ordinal" in ids
    assert ids and all(rule_id.startswith(("p015.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
