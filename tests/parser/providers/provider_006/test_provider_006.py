"""Provider 006 — pending-order style (design §21.8).

Covered shapes:

1. PENDING BUY/SELL LIMIT/STOP canonical forms with triggers;
2. pending lifecycle via common follow-up actions (CANCEL / TRIGGER) with
   action_flags evidence assertions;
3. AMBIGUOUS trigger selection (LIMIT+MARKET never silently picked);
4. DIRECTION conflict → MALFORMED; "@"-adjacency → PARTIAL (no guessing);
5. chat no-signal; raw span exactness; determinism; isolation.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    ConflictKind,
    ParseResultState,
)
from packages.signal_core.enums import EntryTrigger, TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_006"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_006_pending_buy_limit() -> None:
    r = _go("PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.ENTRY_TRIGGER] is EntryTrigger.LIMIT
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_provider_006_pending_sell_stop() -> None:
    r = _go("PENDING SELL STOP EURUSD 1.2500 SL 1.2550 TP 1.2400")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by[CandidateSlot.ENTRY_TRIGGER] is EntryTrigger.STOP
    assert by[CandidateSlot.TP] == (Price(Decimal("1.2400")),)


def test_provider_006_pending_without_tp() -> None:
    r = _go("PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by[CandidateSlot.SL] == Price(Decimal("1.0950"))


def _action_flags(fragment) -> dict[str, object]:
    entries: dict[str, object] = {}
    for evidence in fragment.evidence:
        if evidence.kind == "action_flags":
            for key, value in evidence.fields:
                entries[str(key)] = value
    return entries


def test_provider_006_cancel_pending_lifecycle_with_flags() -> None:
    r = _go("CANCEL PENDING")
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions and actions[0].value.name == "CANCEL"
    assert _action_flags(actions[0]).get("cancel_pending") is True


def test_provider_006_trigger_pending_lifecycle_with_flags() -> None:
    r = _go("TRIGGER PENDING")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions and actions[0].value.name == "MODIFY"
    assert _action_flags(actions[0]).get("trigger_pending") is True


def test_provider_006_ambiguous_triggers_not_silently_picked() -> None:
    r = _go("PENDING BUY LIMIT MARKET EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.AMBIGUOUS
    by = _by_slot(r)
    assert CandidateSlot.ENTRY_TRIGGER not in by
    assert by[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))


def test_provider_006_direction_conflict_malformed() -> None:
    r = _go("PENDING BUY SELL EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c.kind for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.DIRECTION] is ConflictKind.CONFLICTING


def test_provider_006_at_separator_breaks_adjacency_partial() -> None:
    r = _go("PENDING BUY LIMIT EURUSD @ 1.1000")
    assert r.outcome is ParseResultState.PARTIAL
    resolved_entries = [
        f
        for f in r.ir.fragments
        if f.slot is CandidateSlot.ENTRY and f.value is not None
    ]
    assert resolved_entries == []
    resolved_triggers = [
        f
        for f in r.ir.fragments
        if f.slot is CandidateSlot.ENTRY_TRIGGER and f.value is EntryTrigger.LIMIT
    ]
    assert resolved_triggers
    price_values = {str(c.value) for c in r.ir.candidates if c.slot.name == "PRICE"}
    assert "1.1000" in price_values


def test_provider_006_chat_text_no_signal() -> None:
    assert (
        _go("pending review, will confirm tomorrow").outcome
        is ParseResultState.NO_SIGNAL
    )


def test_provider_006_raw_source_spans_are_exact() -> None:
    text = "PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100"
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot.name == "PRICE"]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_006_deterministic() -> None:
    text = "PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_006_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert ids and all(rule_id.startswith(("p006.", "common.")) for rule_id in ids)
