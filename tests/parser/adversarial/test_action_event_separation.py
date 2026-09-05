"""Action vs EVENT/REPORT separation (Phase 2D item 2).

The parser must not turn close-EVENT reports or commentary containing
"close" into executable CLOSE instructions. Primary evidence: real corpus
messages M1 (closed-trade event), M3 (weekly report), M32 (completion
report containing "MANUALLY CLOSE WITH 1150 PIPS") — docs/corpus/
real-messages.md lines 1-38 and 359-374.

Guards exercised here:

1. completion/report markers (COMPLETED / HIT / DONE — corpus M16/M32)
   forbid the common CLOSE action in that message;
2. conservative commentary-modality markers (SHOULD / MAYBE / CONSIDER)
   forbid it likewise — a suppressed close is the safe default; enabling
   imperative closes in such contexts requires provider evidence;
3. plain imperative closes ("CLOSE XAUUSD", "CLOSE HALF", "CLOSE 50%")
   keep working (existing behavior must not change);
4. "CLOSED" (past tense) has never matched the close keyword;
5. M1/M3 remain non-executable under the shared profile (documented
   report-classifier gap: direction+instrument PARTIAL noise is allowed,
   an ACTION is not).
"""

from __future__ import annotations

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from tests.parser._helpers import make_metadata, make_raw, make_runtime

M32 = (
    "THIS FREE GOLD SIGNAL COMPLETED NOW ✅\n"
    "\n"
    "TP1 HIT  70 PIPS+✅\n"
    "\n"
    "TP2 HIT 170 PIPS+✅✅\n"
    "\n"
    "TP3 MANUALLY CLOSE WITH 1150 PIPS+✅✅\n"
    "\n"
    "1:37 RR DONE✅✅✅\n"
    "\n"
    "https://www.tradingview.com/x/RZWgjCC1/\n"
    "\n"
    "Join our Free Group For Latest Updates 👇🏻👇🏻\n"
    "\n"
    "https://t.me/smartearnersacademyllc"
)


def _go(provider: str, text: str):
    return parse(make_raw(text), make_metadata(provider), make_runtime(provider))


def _actions(result):
    return [f.value.name for f in result.ir.fragments if f.slot is CandidateSlot.ACTION]


def _entry(result):
    return next(
        (f.value for f in result.ir.fragments if f.slot is CandidateSlot.ENTRY), None
    )


def test_m32_completion_report_never_close_action() -> None:
    r = _go("provider_001", M32)
    assert _actions(r) == []
    assert r.outcome is ParseResultState.NO_SIGNAL


def test_m32_under_core_real_profile_never_close_action() -> None:
    r = _go("provider_014", M32)
    assert _actions(r) == []
    assert r.outcome is ParseResultState.NO_SIGNAL


def test_minimal_close_with_achievement_marker_suppressed() -> None:
    r = _go("provider_001", "TP3 MANUALLY CLOSE WITH 1150 PIPS+")
    assert _actions(r) == []


def test_plain_imperative_close_still_works() -> None:
    r = _go("provider_001", "CLOSE XAUUSD")
    assert _actions(r) == ["CLOSE"]


def test_close_half_still_works() -> None:
    r = _go("provider_001", "CLOSE HALF")
    assert _actions(r) == ["PARTIAL_CLOSE"]


def test_close_percent_still_works() -> None:
    r = _go("provider_001", "CLOSE 50%")
    assert _actions(r) == ["PARTIAL_CLOSE"]


def test_past_tense_closed_is_not_a_close_instruction() -> None:
    r = _go("provider_001", "🔴 CLOSED - XAUUSD Sell 🔴")
    assert _actions(r) == []
    assert r.outcome is ParseResultState.PARTIAL


def test_commentary_close_suppressed() -> None:
    r = _go("provider_001", "we should close this trade soon")
    assert _actions(r) == []
    assert r.outcome is ParseResultState.NO_SIGNAL


def test_m1_m3_non_executable_no_entry_no_action() -> None:
    m1 = "🔴 CLOSED - XAUUSD Sell 🔴"
    m3 = "♻ Weekly Report ♻"
    for text in (m1, m3):
        r = _go("provider_001", text)
        assert _actions(r) == []
        assert _entry(r) is None


def test_separation_deterministic() -> None:
    for provider, text in (
        ("provider_001", M32),
        ("provider_014", M32),
        ("provider_001", "we should close this trade soon"),
    ):
        first = _go(provider, text)
        second = _go(provider, text)
        assert (first.outcome, first.ir) == (second.outcome, second.ir)
