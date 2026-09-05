"""Provider 014 — real core one-liner/labeled family.

Evidence: docs/corpus/real-messages.md (verbatim fixtures; the corpus's
dominant family). Covered:

1. slash entry ranges → PriceRange + RANGE geometry, both endpoints
   preserved, TP order preserved (M12/M13);
2. repeated unlabeled TPs merge in message order (M11);
3. labeled prose levels: `Stop loss:` SL and repeated `Take profit:` TPs
   (M9, M22) with the STOP-order trigger suppressed for `Stop` labels;
4. `now` → MARKET with the entry preserved (M24);
5. no-entry messages stay PARTIAL with entry_pending (M21 no-TP,
   M22/M25 no-entry); commentary (M6) → NO_SIGNAL;
6. prose range immunity (M9 `300/250 region` never an entry);
7. symbol-adjacent entry (M31) with pip annotations unbound;
8. raw spans exact; determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price, PriceRange
from tests.fixtures.providers.provider_014.canonical import EXAMPLES
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_014"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def _m(name: str) -> str:
    return next(e["raw_text"] for e in EXAMPLES if e["name"] == name)


def test_014_m12_slash_range() -> None:
    r = _go(_m("m12_slash_range_three_tps"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.ENTRY] == PriceRange(
        Price(Decimal(4267)), Price(Decimal(4270))
    )
    assert by[CandidateSlot.ENTRY_GEOMETRY].name == "RANGE"
    assert by[CandidateSlot.SL] == Price(Decimal(4257))
    assert by[CandidateSlot.TP] == (
        Price(Decimal(4278)),
        Price(Decimal(4290)),
        Price(Decimal(4300)),
    )


def test_014_m13_range_and_tail_prose() -> None:
    r = _go(_m("m13_slash_range_sell"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.ENTRY] == PriceRange(
        Price(Decimal(4066)), Price(Decimal(4070))
    )
    assert by[CandidateSlot.TP] == (
        Price(Decimal(4055)),
        Price(Decimal(4040)),
        Price(Decimal(4020)),
    )


def test_014_m9_labeled_levels() -> None:
    r = _go(_m("m9_labeled_levels_repeated_take_profit"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("4302.00"))
    assert by[CandidateSlot.ENTRY_TRIGGER] is not None
    assert by[CandidateSlot.ENTRY_TRIGGER].name == "LIMIT"
    assert by[CandidateSlot.SL] == Price(Decimal("4273.00"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal("4320.00")),
        Price(Decimal("4375.00")),
        Price(Decimal("4525.00")),
    )


def test_014_m9_prose_range_never_entry() -> None:
    r = _go(_m("m9_labeled_levels_repeated_take_profit"))
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("4302.00"))
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "300" in unbound and "250" in unbound


def test_014_m11_repeated_tp_order() -> None:
    r = _go(_m("m11_repeated_unlabeled_tp"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("4596.00"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal(4592)),
        Price(Decimal(4588)),
        Price(Decimal(4581)),
        Price(Decimal(4560)),
    )
    assert by[CandidateSlot.SL] == Price(Decimal(4601))


def test_014_m10_core_adjacency() -> None:
    r = _go(_m("m10_core_adjacency_colon_labels"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "USDJPY"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("159.31"))
    assert by[CandidateSlot.SL] == Price(Decimal("158.81"))
    assert by[CandidateSlot.TP] == (Price(Decimal("160.81")),)


def test_014_m17_two_line_core() -> None:
    r = _go(_m("m17_two_line_core"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "XAUUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal(4425))


def test_014_m21_lowercase_limit_no_tp_partial() -> None:
    r = _go(_m("m21_one_liner_limit_no_tp"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("4342.72"))
    assert by[CandidateSlot.ENTRY_TRIGGER].name == "LIMIT"
    assert by[CandidateSlot.SL] == Price(Decimal("4324.74"))
    assert by.get(CandidateSlot.TP) is None
    assert r.ir.unresolved_fields == ()


def test_014_m22_no_entry_partial_and_no_stop_trigger() -> None:
    r = _go(_m("m22_no_entry_stop_loss_label"))
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by.get(CandidateSlot.ENTRY) is None
    assert by.get(CandidateSlot.ENTRY_TRIGGER) is None
    assert by[CandidateSlot.SL] == Price(Decimal("52953.2"))
    assert by[CandidateSlot.TP] == (
        Price(Decimal("52755.4")),
        Price(Decimal("52625.1")),
    )
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence} | {
        e.kind for e in r.ir.evidence
    }
    assert "entry_pending" in kinds


def test_014_m24_sell_now_market() -> None:
    r = _go(_m("m24_sell_now_market"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("4133.00"))
    assert by[CandidateSlot.ENTRY_TRIGGER] is not None
    assert by[CandidateSlot.ENTRY_TRIGGER].name == "MARKET"
    assert by[CandidateSlot.ENTRY_GEOMETRY].name == "MARKET"
    assert by[CandidateSlot.SL] == Price(Decimal("4152.00"))
    assert by[CandidateSlot.TP] == (Price(Decimal("4076.00")),)


def test_014_m25_no_entry_partial() -> None:
    r = _go(_m("m25_no_entry_gold"))
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "XAUUSD"
    assert by.get(CandidateSlot.ENTRY) is None
    assert by[CandidateSlot.SL] == Price(Decimal("4168.00"))
    assert by[CandidateSlot.TP] == (Price(Decimal("4088.00")),)


def test_014_m31_core_entry_annotations_unbound() -> None:
    r = _go(_m("m31_core_emoji_annotations"))
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("100.814"))
    assert by[CandidateSlot.SL] == Price(Decimal("100.564"))
    assert by[CandidateSlot.TP] == (Price(Decimal("101.064")),)
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "25" in unbound


def test_014_m6_commentary_no_signal() -> None:
    r = _go(_m("m6_commentary_no_signal"))
    assert r.outcome is ParseResultState.NO_SIGNAL
    assert r.ir.fragments == ()


def test_014_conflicting_directions_malformed() -> None:
    r = _go("XAUUSD BUY 4267 SELL 4270\nSL 4257")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.DIRECTION].kind.name == "CONFLICTING"


def test_014_raw_source_spans_are_exact() -> None:
    text = _m("m12_slash_range_three_tps")
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_014_deterministic() -> None:
    text = _m("m12_slash_range_three_tps")
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_014_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.trigger.stop" not in ids
    assert "p014.entry.range" in ids and "p014.sl.regex" in ids
    assert ids and all(rule_id.startswith(("p014.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
