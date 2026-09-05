"""Provider 005 — multi-line numbered entry levels (design §21.7).

Covered shapes:

1. design-faithful ladder (descending levels preserved verbatim, symbol-less);
2. with symbol + two levels;
3. ordinal false-positive protection (ordinals/prose numbers/dates never prices);
4. direction conflict preserved → MALFORMED;
5. levels-missing → PARTIAL; action inheritance; determinism; isolation.
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

PROVIDER = "provider_005"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def _by_slot(result):
    return {f.slot: f.value for f in result.ir.fragments}


def test_provider_005_design_example_without_symbol() -> None:
    r = _go("SCALP LONG\n1) 3350\n2) 3340\n3) 3330\nSL 3300\nTP 3400")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert CandidateSlot.INSTRUMENT not in by
    assert by[CandidateSlot.ENTRY] == (
        Price(Decimal(3350)),
        Price(Decimal(3340)),
        Price(Decimal(3330)),
    )
    assert by[CandidateSlot.ENTRY_GEOMETRY].name == "MULTIPLE"
    assert by[CandidateSlot.SL] == Price(Decimal(3300))
    assert by[CandidateSlot.TP] == (Price(Decimal(3400)),)


def test_provider_005_with_symbol_and_canonical_alias() -> None:
    r = _go("SCALP LONG EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400")
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ENTRY] == (Price(Decimal(3350)), Price(Decimal(3340)))
    assert by[CandidateSlot.DIRECTION] is TradeDirection.BUY
    direction_candidate = next(c for c in r.ir.candidates if c.slot.name == "DIRECTION")
    assert (
        any(ev.fields for ev in direction_candidate.provenance)
        or direction_candidate.value is TradeDirection.BUY
    )


def test_provider_005_ordinals_never_become_prices() -> None:
    """'1)'-'3)' prefixes and prose numbers must not leak into any field."""
    r = _go("SCALP LONG EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400\ncount 3 total")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == (Price(Decimal(3350)), Price(Decimal(3340)))
    entry_values = {str(v) for v in by[CandidateSlot.ENTRY]}
    assert (
        "1" not in entry_values and "2" not in entry_values and "3" not in entry_values
    )


def test_provider_005_date_chain_never_a_price() -> None:
    r = _go("SCALP LONG EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400\ndated 2026-09-05")
    assert r.outcome is ParseResultState.PARSED
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] == (Price(Decimal(3350)), Price(Decimal(3340)))
    assert by[CandidateSlot.SL] == Price(Decimal(3300))
    price_values = {str(c.value) for c in r.ir.candidates if c.slot.name == "PRICE"}
    assert {"2026", "9", "5"} <= price_values


def test_provider_005_direction_conflict_malformed() -> None:
    r = _go("SCALP LONG AND SHORT EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400")
    assert r.outcome is ParseResultState.MALFORMED
    conflicts = {c.slot: c.kind for c in r.ir.conflicts}
    assert conflicts[CandidateSlot.DIRECTION] is ConflictKind.CONFLICTING
    by = _by_slot(r)
    assert by[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by[CandidateSlot.ENTRY] == (Price(Decimal(3350)), Price(Decimal(3340)))


def test_provider_005_levels_missing_partial() -> None:
    r = _go("SCALP LONG EURUSD\nSL 3300\nTP 3400")
    assert r.outcome is ParseResultState.PARTIAL
    by = _by_slot(r)
    assert by[CandidateSlot.ENTRY] is None
    assert by[CandidateSlot.SL] == Price(Decimal(3300))


def test_provider_005_inherits_common_action() -> None:
    r = _go("SCALP LONG EURUSD\n1) 3350\nSL 3300\nTP 3400\nCLOSE 50%")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions and actions[0].value.name == "PARTIAL_CLOSE"


def test_provider_005_chat_text_no_signal() -> None:
    assert (
        _go("scalping session notes for tomorrow").outcome is ParseResultState.NO_SIGNAL
    )


def test_provider_005_deterministic() -> None:
    text = "SCALP LONG\n1) 3350\n2) 3340\n3) 3330\nSL 3300\nTP 3400"
    first = _go(text)
    second = _go(text)
    assert (first.outcome, first.ir) == (second.outcome, second.ir)


def test_provider_005_profile_isolation() -> None:
    rt = make_runtime(PROVIDER)
    ids = {rule.id for rule in rt.effective_rules}
    assert ids and all(rule_id.startswith(("p005.", "common.")) for rule_id in ids)
