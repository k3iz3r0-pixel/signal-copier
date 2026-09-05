"""Provider 017 — real prose-at-entry / NOW-wording family.

Evidence: docs/corpus/real-messages.md M16, M27, M30 (verbatim fixtures).

Covered:

1. `SELL NOW at` → MARKET trigger + at-entry (M30);
2. `SELL LIMIT now at` → LIMIT only; the adverb `now` must NOT become a
   MARKET trigger (FORBIDS-gated REGEX rule; M27) — no AMBIGUOUS_TRIGGER;
3. `Move SL at <num>` follow-up → ACTION_MOVE_SL with the level in the
   evidence snippet; `TP1 HIT` status line never binds (M16);
4. ordinal `TP1:/TP2:` and labeled `TP:` TPs; pip annotations unbound;
5. prose commentary → NO_SIGNAL; raw spans exact; determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.enums import InstructionType, TradeDirection
from packages.signal_core.value_objects import Price
from tests.fixtures.providers.provider_017.canonical import EXAMPLES
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_017"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def _m(name: str) -> str:
    return next(e["raw_text"] for e in EXAMPLES if e["name"] == name)


def test_017_m30_sell_now_market() -> None:
    r = _go(_m("m30_sell_now_at"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.INSTRUMENT] == "GBPCHF"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.08280"))
    assert by[CandidateSlot.ENTRY_TRIGGER] is not None
    assert by[CandidateSlot.ENTRY_TRIGGER].name == "MARKET"
    assert by[CandidateSlot.ENTRY_GEOMETRY].name == "MARKET"
    assert by[CandidateSlot.SL] == Price(Decimal("1.08500"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.07750")),)


def test_017_m30_pip_annotations_unbound() -> None:
    r = _go(_m("m30_sell_now_at"))
    bound = {str(f.value) for f in r.ir.fragments}
    for annotation in ("53", "22", "2"):
        assert annotation not in bound
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    for annotation in ("53", "22", "2"):
        assert annotation in unbound


def test_017_m27_limit_not_market() -> None:
    r = _go(_m("m27_forecast_sell_limit"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY_TRIGGER] is not None
    assert by[CandidateSlot.ENTRY_TRIGGER].name == "LIMIT"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.17725"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.17825"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal("1.17350")),
        Price(Decimal("1.16700")),
    )
    assert r.ir.ambiguities == ()


def test_017_m27_forecast_prose_immune() -> None:
    r = _go(_m("m27_forecast_sell_limit"))
    bound = {str(f.value) for f in r.ir.fragments}
    assert "75" not in bound


def test_017_m16_move_sl_action() -> None:
    r = _go(_m("m16_move_sl_at_follow_up"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "XAUUSD"
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL
    action_frags = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    snippets = [e.snippet for f in action_frags for e in f.evidence if e.snippet]
    assert "4420" in snippets


def test_017_m16_status_line_never_binds() -> None:
    r = _go(_m("m16_move_sl_at_follow_up"))
    by = _by_slot(r)
    assert by.get(CandidateSlot.ENTRY) is None
    assert by.get(CandidateSlot.TP) is None
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "4420" in unbound and "100" in unbound


def test_017_commentary_no_signal() -> None:
    assert _go("we watch this pair later if support breaks").outcome is (
        ParseResultState.NO_SIGNAL
    )


def test_017_direction_keyword_prose_partial_not_executable() -> None:
    r = _go("we may sell later if support breaks")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by.get(CandidateSlot.ENTRY) is None


def test_017_raw_source_spans_are_exact() -> None:
    text = _m("m30_sell_now_at")
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_017_deterministic() -> None:
    text = _m("m27_forecast_sell_limit")
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_017_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.tp.number" not in ids and "common.condition.at_price" not in ids
    assert "p017.trigger.now" in ids and "p017.action.move_sl_at" in ids
    assert ids and all(rule_id.startswith(("p017.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
