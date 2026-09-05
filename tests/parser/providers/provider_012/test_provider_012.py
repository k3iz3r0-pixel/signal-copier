"""Provider 012 — follow-up action family (INFERENCE).

Covered shapes:

1. MOVE SL TO x standalone → §20.13 follow_up_only (NO_SIGNAL + ACTION
   MOVE_SL + TARGET_LAST_SIGNAL correlation);
2. instrument-bearing and inherited common forms → PARSED actions;
3. conflicting actions → MALFORMED with both preserved;
4. parenthetical "was" numbers never bind (false-positive axis);
5. chat prose → NO_SIGNAL; raw spans exact; determinism; isolation.
"""

from __future__ import annotations

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ConflictKind, ParseResultState
from packages.signal_core.enums import InstructionType
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_012"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_012_standalone_move_sl_is_follow_up() -> None:
    r = _go("MOVE SL TO 1.0900")
    assert r.outcome is ParseResultState.NO_SIGNAL
    by = _by_slot(r)
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL
    kinds = {e.kind for f in r.ir.fragments for e in f.evidence} | {
        e.kind for e in r.ir.evidence
    }
    assert "follow_up_only" in kinds
    assert r.ir.correlation_request is not None
    assert r.ir.correlation_request.kind.name == "TARGET_LAST_SIGNAL"


def test_provider_012_instrument_move_sl_parsed() -> None:
    r = _go("EURUSD MOVE SL 1.0900")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL


def test_provider_012_bare_sl_form_inherited() -> None:
    r = _go("EURUSD SL 1.0900")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL


def test_provider_012_move_tp_parsed() -> None:
    r = _go("MOVE TP TO 1.1300")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_TP


def test_provider_012_breakeven_inherited() -> None:
    r = _go("MOVE SL TO BE")
    assert r.outcome is ParseResultState.PARSED
    assert _by_slot(r)[CandidateSlot.ACTION] is InstructionType.BREAKEVEN


def test_provider_012_conflicting_actions_malformed() -> None:
    r = _go("MOVE SL TO 1.0900 MOVE TP TO 1.1300")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.ACTION].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[CandidateSlot.ACTION].involved} == {
        InstructionType.MOVE_SL,
        InstructionType.MOVE_TP,
    }


def test_provider_012_modify_plus_move_conflict() -> None:
    r = _go("CHANGE ENTRY TO 1.1020 MOVE SL TO 1.0900")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c for c in r.ir.conflicts}
    assert {c.value for c in conflicts[CandidateSlot.ACTION].involved} == {
        InstructionType.MODIFY,
        InstructionType.MOVE_SL,
    }


def test_provider_012_update_context_number_never_binds() -> None:
    r = _go("GBPUSD MOVE SL TO 1.2500 TP 1.2600")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL
    assert by.get(CandidateSlot.TP) is None
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "1.2600" in unbound


def test_provider_012_was_parenthetical_never_binds() -> None:
    r = _go("MOVE SL TO 1.0900 (was 1.0850)")
    assert r.outcome is ParseResultState.NO_SIGNAL
    by = _by_slot(r)
    assert by[CandidateSlot.ACTION] is InstructionType.MOVE_SL
    unbound = {str(c.value) for c in r.ir.candidates if c.slot is CandidateSlot.PRICE}
    assert "1.0850" in unbound


def test_provider_012_chat_text_no_signal() -> None:
    assert _go("please move the sl sometime").outcome is ParseResultState.NO_SIGNAL


def test_provider_012_raw_source_spans_are_exact() -> None:
    text = "EURUSD MOVE SL TO 1.0900"
    r = _go(text)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    assert price_candidates
    for candidate in price_candidates:
        span = candidate.source_span
        assert text[span.start : span.end] == str(candidate.value)


def test_provider_012_deterministic() -> None:
    text = "MOVE SL TO 1.0900"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_012_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert "p012.action.move_sl_to" in ids
    assert "common.action.move_sl" in ids
    assert ids and all(rule_id.startswith(("p012.", "common.")) for rule_id in ids)
    before = {rule.id for rule in make_runtime("provider_001").effective_rules}
    make_runtime(PROVIDER)
    after = {rule.id for rule in make_runtime("provider_001").effective_rules}
    assert before == after
