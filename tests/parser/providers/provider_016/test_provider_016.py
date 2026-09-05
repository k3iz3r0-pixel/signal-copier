"""Provider 016 — real @-separated levels family.

Evidence: docs/corpus/real-messages.md M23, M26 (verbatim fixtures).

Covered:

1. `@` glue binds `SL @ x` / `TP @ x`; entry via the BEFORE_TOKEN SL zone
   (SL value owned by the SL rule, never double-bound);
2. `Tp1/Tp2` ordinal TPs; ordinal digits (1/2) never bind;
3. XAGUSD and GOLD→XAUUSD aliases; prose header immunity;
4. raw spans exact; determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.fixtures.providers.provider_016.canonical import EXAMPLES
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_016"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def _m(name: str) -> str:
    return next(e["raw_text"] for e in EXAMPLES if e["name"] == name)


def test_016_m23_at_levels() -> None:
    r = _go(_m("m23_at_separator_levels"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.INSTRUMENT] == "XAGUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("65.1950"))
    assert by[CandidateSlot.SL] == Price(Decimal("67.0731"))
    assert by[CandidateSlot.TP] == (Price(Decimal("61.3857")),)


def test_016_m26_ordinal_tps() -> None:
    r = _go(_m("m26_at_entry_ordinal_tps"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "XAUUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("4103.210"))
    assert by[CandidateSlot.SL] == Price(Decimal("4112.757"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal("4079.387")),
        Price(Decimal("4058.731")),
    )


def test_016_sl_never_double_bound_as_entry() -> None:
    r = _go(_m("m26_at_entry_ordinal_tps"))
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] != by[CandidateSlot.SL]
    assert r.ir.conflicts == ()


def test_016_ordinal_digits_never_bind() -> None:
    r = _go(_m("m26_at_entry_ordinal_tps"))
    bound = {str(f.value) for f in r.ir.fragments}
    assert "1" not in bound and "2" not in bound
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "1" in unbound and "2" in unbound


def test_016_prose_header_ignored() -> None:
    r = _go(_m("m23_at_separator_levels"))
    assert r.ir.conflicts == ()


def test_016_chat_text_no_signal() -> None:
    assert _go("we watch this pair later today").outcome is ParseResultState.NO_SIGNAL


def test_016_direction_keyword_prose_partial_not_executable() -> None:
    r = _go("we may sell later today")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by.get(CandidateSlot.ENTRY) is None


def test_016_raw_source_spans_are_exact() -> None:
    text = _m("m23_at_separator_levels")
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_016_deterministic() -> None:
    text = _m("m23_at_separator_levels")
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_016_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.tp.number" not in ids
    assert "p016.entry.before_sl" in ids and "p016.tp.at" in ids
    assert ids and all(rule_id.startswith(("p016.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
