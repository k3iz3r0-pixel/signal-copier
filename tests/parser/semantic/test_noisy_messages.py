"""Regression tests for noise/irrelevant-number handling.

The prompt requires: "Do not silently interpret every number as a price."
These tests prove that a bare number in chat text does NOT get bound to
the ENTRY slot by the parser, even though the generic candidate
extraction emits a pre-rule PRICE candidate for every numeric token.

What we verify here:

- Chat text with a number produces NO_SIGNAL and NO ENTRY fragment.
- A number near a direction keyword but without instrument/SL/TP is still
  NOT bound to ENTRY (the ``p001.entry.first`` rule requires a direction
  keyword AND a context, not just any number).
- A range in chat text is NOT bound to ENTRY.
- Pure numbers in otherwise meaningless context produce NO_SIGNAL.
- The pre-rule PRICE candidate is still emitted (generic extraction is
  honest about what was seen) but no rule binds it to a semantic slot
  without a real signal structure.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.parser import parse
from packages.parser.enums import CandidateSlot, MessageEvent, ParseResultState
from packages.parser.types import MessageMetadata, RawMessage
from packages.parser_profiles import get_profile
from packages.signal_core.enums import SourceType

PROVIDER = "provider_001"


def _md() -> MessageMetadata:
    return MessageMetadata(
        provider_name=PROVIDER,
        source_type=SourceType.TELEGRAM,
        timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        message_event=MessageEvent.CREATE,
    )


def _raw(text: str) -> RawMessage:
    return RawMessage(raw_text=text, media_refs=(), raw_payload_hash="")


def test_chat_text_with_number_does_not_emit_entry() -> None:
    """Regression: 'hello friends, the number is 42' must NOT produce an
    ENTRY fragment. The generic PRICE candidate is preserved as evidence
    but no rule binds it to a semantic slot."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("hello friends, see you tomorrow, the number is 42"), _md(), rt)
    assert r.outcome is ParseResultState.NO_SIGNAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert not entry_fragments
    geometry_fragments = [
        f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY_GEOMETRY
    ]
    assert not geometry_fragments


def test_chat_text_with_range_does_not_emit_entry() -> None:
    """Regression: 'between 50-60' in chat must NOT produce an ENTRY
    fragment. A range in prose is not a signal."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("the price will be between 50-60 tomorrow"), _md(), rt)
    assert r.outcome is ParseResultState.NO_SIGNAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert not entry_fragments


def test_bare_number_does_not_emit_entry() -> None:
    """A single number with no signal context must not be bound to ENTRY."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("42"), _md(), rt)
    assert r.outcome is ParseResultState.NO_SIGNAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert not entry_fragments


def test_direction_with_number_but_no_instrument_does_not_emit_entry() -> None:
    """'BUY at 42' has a direction keyword AND a number, but no recognized
    instrument. The p001.entry.first rule now requires a direction
    keyword AND a symbol token, so it does NOT fire here. The outcome
    is PARTIAL (direction-only, awaiting follow-up) — not a silent
    ENTRY interpretation.
    """
    rt = get_profile(PROVIDER)
    r = parse(_raw("BUY at 42"), _md(), rt)
    assert r.outcome is ParseResultState.PARTIAL
    entry_fragments = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    # ENTRY may be emitted as an UNRESOLVED placeholder (None value);
    # it must NOT be bound to a real Price value.
    for fragment in entry_fragments:
        assert fragment.value is None, (
            f"ENTRY bound to {fragment.value!r} without a real "
            "signal structure (instrument + SL anchor required)"
        )


def test_pre_rule_price_candidate_is_preserved_for_audit() -> None:
    """The generic extraction does emit a pre-rule PRICE candidate for
    every numeric token. This is the honest representation of what was
    seen. The audit-friendly behavior is: candidates are preserved
    even when no rule binds them to a semantic slot."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("hello friends, the number is 42"), _md(), rt)
    price_candidates = [c for c in r.ir.candidates if c.slot is CandidateSlot.PRICE]
    # The pre-rule PRICE candidate is still in the IR for audit.
    assert price_candidates


def test_real_signal_still_parses_after_noise_fix() -> None:
    """The fix must not break real signals. A canonical signal still
    parses to PARSED with all expected fragments."""
    rt = get_profile(PROVIDER)
    r = parse(
        _raw("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100"),
        _md(),
        rt,
    )
    assert r.outcome is ParseResultState.PARSED
    direction_fragments = [
        f for f in r.ir.fragments if f.slot is CandidateSlot.DIRECTION
    ]
    assert direction_fragments[0].value.name == "BUY"  # type: ignore[attr-defined]
    instrument_fragments = [
        f for f in r.ir.fragments if f.slot is CandidateSlot.INSTRUMENT
    ]
    assert instrument_fragments[0].value == "EURUSD"


def test_signal_without_sl_still_parses_after_noise_fix() -> None:
    """A signal with direction+instrument+entry but no SL/TP is still a
    parseable signal (PARSED), not silently rejected."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("BUY EURUSD 1.1000"), _md(), rt)
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION].name == "BUY"  # type: ignore[attr-defined]
    assert by_slot[CandidateSlot.INSTRUMENT] == "EURUSD"


def test_move_sl_to_entry_is_treated_as_breakeven() -> None:
    """'MOVE SL TO ENTRY' is semantically equivalent to breakeven.
    The contract supports BREAKEVEN as a distinct InstructionType;
    the common rule recognizes BE / BREAKEVEN / ENTRY as the target
    phrase. The action fragment is emitted with value=BREAKEVEN."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("MOVE SL TO ENTRY"), _md(), rt)
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions
    assert actions[0].value.name == "BREAKEVEN"  # type: ignore[attr-defined]


def test_breakeven_with_be_phrase_still_recognized() -> None:
    """Regression: the original 'MOVE SL TO BE' phrase must still work
    after extending the breakeven regex."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("MOVE SL TO BE"), _md(), rt)
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions
    assert actions[0].value.name == "BREAKEVEN"  # type: ignore[attr-defined]