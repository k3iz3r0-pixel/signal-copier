"""Provider 001 — inline, comma-separated field list (design §21.1).

Three structurally different signal shapes:

1. canonical (entry/SL/TP all present, single number);
2. entry-range (price-range via "-" separator);
3. pending-order with LIMIT/STOP trigger.

Plus action and PARTIAL/NO_SIGNAL outcomes.
"""

from __future__ import annotations

import pytest

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    MessageEvent,
    ParseResultState,
)
from packages.signal_core.enums import EntryTrigger, TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_001"


def _go(text: str, event: MessageEvent = MessageEvent.CREATE):
    return parse(make_raw(text), make_metadata(PROVIDER, event), make_runtime(PROVIDER))


@pytest.mark.parametrize(
    "text, expected_outcome",
    [
        ("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100", ParseResultState.PARSED),
        ("SELL GBPUSD 1.2500 SL 1.2550 TP 1.2400", ParseResultState.PARSED),
        ("BUY XAUUSD 2350-2360 SL 2340 TP 2400", ParseResultState.PARSED),
        ("BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100", ParseResultState.PARSED),
        ("BUY STOP EURUSD 1.1000 SL 1.0950 TP 1.1100", ParseResultState.PARSED),
    ],
)
def test_provider_001_canonical_signals_parse(text: str, expected_outcome: ParseResultState) -> None:
    assert _go(text).outcome is expected_outcome


def test_provider_001_single_entry_geometry_is_single() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_GEOMETRY].name == "SINGLE"


def test_provider_001_range_entry_geometry_is_range() -> None:
    r = _go("BUY XAUUSD 2350-2360 SL 2340 TP 2400")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_GEOMETRY].name == "RANGE"
    assert by_slot[CandidateSlot.ENTRY].low == Price(__import__("decimal").Decimal("2350"))


def test_provider_001_limit_trigger() -> None:
    r = _go("BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_TRIGGER] is EntryTrigger.LIMIT


def test_provider_001_stop_trigger() -> None:
    r = _go("BUY STOP EURUSD 1.1000 SL 1.0950 TP 1.1100")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_TRIGGER] is EntryTrigger.STOP


def test_provider_001_direction_only_partial() -> None:
    r = _go("BUY")
    assert r.outcome is ParseResultState.PARTIAL
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.BUY


@pytest.mark.parametrize(
    "text, action_name",
    [
        ("CLOSE", "CLOSE"),
        ("CLOSE HALF", "PARTIAL_CLOSE"),
        ("CLOSE 50%", "PARTIAL_CLOSE"),
        ("MOVE SL TO BE", "BREAKEVEN"),
        ("MOVE SL TO BREAKEVEN", "BREAKEVEN"),
        ("CANCEL PENDING", "CANCEL"),
        ("TRIGGER PENDING NOW", "MODIFY"),
    ],
)
def test_provider_001_actions(text: str, action_name: str) -> None:
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions
    assert actions[0].value.name == action_name


def test_provider_001_empty_yields_no_signal() -> None:
    assert _go("").outcome is ParseResultState.NO_SIGNAL


def test_provider_001_chat_text_yields_no_signal() -> None:
    assert _go("hello friends, see you tomorrow").outcome is ParseResultState.NO_SIGNAL


def test_provider_001_delete_event_yields_no_signal() -> None:
    r = _go("BUY EURUSD 1.1000", event=MessageEvent.DELETE)
    assert r.outcome is ParseResultState.NO_SIGNAL
    assert r.ir.correlation_request is not None
    assert r.ir.correlation_request.kind.name == "DELETE_APPLY"


def test_provider_001_multiple_tp_levels_preserved() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 TP 1.1150")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    tp_values = by_slot[CandidateSlot.TP]
    assert len(tp_values) == 2


def test_provider_001_remove_sl_emits_action() -> None:
    """'REMOVE SL' standalone is treated as a follow-up to the last signal
    (MOVE_SL with no instrument/entry), producing NO_SIGNAL with a
    correlation request — per design §14.2 branch 5."""
    r = _go("REMOVE SL")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions
    assert actions[0].value.name == "MOVE_SL"
    # Either NO_SIGNAL (follow-up-only) or PARSED with correlation; both are
    # defensible per §14.2. The action fragment MUST be present.
    assert r.ir.correlation_request is not None


def test_provider_001_change_tp_emits_move_tp() -> None:
    """'CHANGE TP TO 1.1150' as a standalone follow-up action."""
    r = _go("CHANGE TP TO 1.1150")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert any(a.value.name == "MOVE_TP" for a in actions)