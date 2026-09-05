"""Provider 007 — ordinal take-profit labels (INFERENCE family).

Covered shapes:

1. TP1/TP2(/TP3) labels accumulate in message order; ordinals never prices;
2. common.tp.number exclusion is effective (no ordinal mis-binding);
3. BETWEEN_ANCHORS entry binding, including reordered fields;
4. ENTRY conflict preserved → MALFORMED; missing entry → PARTIAL;
5. prose noise safety; common action inheritance; raw span exactness;
   determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    ConflictKind,
    ParseResultState,
)
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_007"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_007_buy_two_labeled_tps() -> None:
    r = _go("BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")), Price(Decimal("1.1200")))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))


def test_provider_007_sell_three_labeled_tps() -> None:
    r = _go("SELL EURUSD 1.2500 TP1 1.2400 TP2 1.2300 TP3 1.2200 SL 1.2550")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.TP] == (
        Price(Decimal("1.2400")),
        Price(Decimal("1.2300")),
        Price(Decimal("1.2200")),
    )


def test_provider_007_ordinal_digits_never_prices_or_tps() -> None:
    r = _go("BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950")
    by = _by_slot(r)
    tp_values = {str(v) for v in by[CandidateSlot.TP]}
    assert "1" not in tp_values and "2" not in tp_values
    price_values = {str(c.value) for c in r.ir.candidates if c.slot.name == "PRICE"}
    assert "1" in price_values and "2" in price_values


def test_provider_007_common_tp_rule_is_excluded() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.tp.number" not in ids
    assert "p007.tp.labeled" in ids


def test_provider_007_reordered_fields() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP1 1.1100 TP2 1.1200")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")), Price(Decimal("1.1200")))


def test_provider_007_two_entries_conflict_malformed() -> None:
    r = _go("BUY EURUSD 1.1000 1.1050 TP1 1.1100 TP2 1.1200 SL 1.0950")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c.kind for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.ENTRY] is ConflictKind.CONFLICTING
    by = _by_slot(r)
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")), Price(Decimal("1.1200")))


def test_provider_007_missing_entry_partial() -> None:
    r = _go("BUY EURUSD TP1 1.1100 TP2 1.1200 SL 1.0950")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")), Price(Decimal("1.1200")))


def test_provider_007_prose_noise_never_a_price() -> None:
    r = _go(
        "BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950\nnote: level count 2 max"
    )
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")), Price(Decimal("1.1200")))


def test_provider_007_inherits_common_action() -> None:
    r = _go("BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950\nCLOSE 30% AT 1.1100")
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions and actions[0].value.name == "PARTIAL_CLOSE"
    conditions = r.ir.conditions
    assert conditions and conditions[0].kind.name == "AT_PRICE"


def test_provider_007_chat_text_no_signal() -> None:
    assert (
        _go("tp1 and tp2 labels explained soon").outcome is ParseResultState.NO_SIGNAL
    )


def test_provider_007_raw_source_spans_are_exact() -> None:
    text = "BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950"
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot.name == "PRICE"]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_007_deterministic() -> None:
    text = "BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_007_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert ids and all(rule_id.startswith(("p007.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert "common.tp.number" in before and "common.tp.number" in after
