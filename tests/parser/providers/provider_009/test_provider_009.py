"""Provider 009 — prose synonym family (INFERENCE).

Covered shapes:

1. Long/Short canonical mapping with Stop/Target synonyms (any casing);
2. common.trigger.stop exclusion (prose "Stop" is never a pending trigger);
3. common.condition.at_price exclusion ("at <price>" → PARTIAL, no guessing);
4. direction + entry conflicts preserved → MALFORMED;
5. signal+action message keeps signal fragments;
6. chat prose → NO_SIGNAL; raw spans exact; determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ConflictKind, ParseResultState
from packages.signal_core.enums import InstructionType, TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_009"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_009_long_canonical_mapping() -> None:
    r = _go("Long EURUSD 1.1000. Stop 1.0950. Target 1.1100.")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence}
    assert "canonical_alias" in kinds


def test_provider_009_short_lowercase_prose() -> None:
    r = _go("We go short EURUSD 1.2500 stop 1.2550 target 1.2400 now")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.2500"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.2550"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.2400")),)


def test_provider_009_canonical_labels_still_work() -> None:
    r = _go("Long EURUSD 1.1000. SL 1.0950. TP 1.1100.")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_provider_009_prose_stop_is_never_a_trigger() -> None:
    r = _go("Long EURUSD 1.1000. Stop 1.0950. Target 1.1100.")
    by = _by_slot(r)
    assert by.get(CandidateSlot.ENTRY_TRIGGER, "absent") in (None, "absent")
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.trigger.stop" not in ids


def test_provider_009_direction_conflict_malformed() -> None:
    r = _go("Long EURUSD 1.1000. Stop 1.0950. Target 1.1100. Short EURUSD 1.1500.")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.DIRECTION].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[CandidateSlot.DIRECTION].involved} == {
        TradeDirection.BUY,
        TradeDirection.SELL,
    }
    assert conflicts[CandidateSlot.ENTRY].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[CandidateSlot.ENTRY].involved} == {
        Price(Decimal("1.1000")),
        Price(Decimal("1.1500")),
    }


def test_provider_009_entry_preposition_partial() -> None:
    r = _go("Long EURUSD at 1.1000. Stop 1.0950. Target 1.1100.")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "1.1000" in unbound
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence}
    assert "entry_pending" in kinds


def test_provider_009_signal_plus_action_keeps_signal_fragments() -> None:
    r = _go("Long EURUSD 1.1000. Stop 1.0950. Target 1.1100. CLOSE HALF")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.ACTION] is InstructionType.PARTIAL_CLOSE


def test_provider_009_chat_text_no_signal() -> None:
    assert _go("stop loss and target talk, no trade").outcome is (
        ParseResultState.NO_SIGNAL
    )


def test_provider_009_raw_source_spans_are_exact() -> None:
    text = "Long EURUSD 1.1000. Stop 1.0950. Target 1.1100."
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_009_deterministic() -> None:
    text = "Long EURUSD 1.1000. Stop 1.0950. Target 1.1100."
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_009_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "common.sl.number" not in ids and "common.tp.number" not in ids
    assert "p009.sl.stopword" in ids and "p009.tp.targetword" in ids
    assert ids and all(rule_id.startswith(("p009.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
