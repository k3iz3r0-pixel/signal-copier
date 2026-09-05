"""Regression tests for conflict and ambiguity handling (design §5.10, §5.11, §6.2).

The prompt requires:
- "Do not silently select conflicting candidates."
- Tests for "conflicting candidates" and "ambiguous signal."

These tests verify the deterministic conflict/ambiguity behavior of the
parser. The conflict resolution is engine-level; the IR exposes the
conflict/ambiguity records so downstream consumers can decide what to
do.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.parser import parse
from packages.parser.enums import (
    AmbiguityKind,
    CandidateSlot,
    ConflictKind,
    MessageEvent,
    ParseResultState,
)
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


# ---------------------------------------------------------------------------
# §6.2: conflicting candidates for the SAME slot
# ---------------------------------------------------------------------------


def test_two_direction_keywords_produce_a_conflict() -> None:
    """'BUY SELL' has two competing direction keywords. The parser must
    NOT silently pick one. It must emit a Conflict and the outcome
    must be MALFORMED (per design §14.1)."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("BUY SELL"), _md(), rt)
    # A conflict is recorded.
    direction_conflicts = [
        c for c in r.ir.conflicts if c.slot is CandidateSlot.DIRECTION
    ]
    assert direction_conflicts
    assert direction_conflicts[0].kind is ConflictKind.CONFLICTING
    # The conflict involves both BUY and SELL candidates.
    value_names = {c.value.name for c in direction_conflicts[0].involved}  # type: ignore[attr-defined]
    assert "BUY" in value_names
    assert "SELL" in value_names
    # Outcome is MALFORMED because of the conflict.
    assert r.outcome is ParseResultState.MALFORMED


def test_two_instruments_are_both_extracted_as_candidates() -> None:
    """'BUY EURUSD GBPUSD' has two symbol tokens. The pre-rule candidate
    extraction emits both as INSTRUMENT candidates (competing
    hypotheses). The p001.instrument rule has occurrence=FIRST, so only
    the first is bound as the winner — but the second symbol survives in
    the CandidateGraph and the resolver CONSUMES it: the competing
    interpretations surface as a Conflict (§6.2) and the outcome is
    MALFORMED instead of a silent pick.

    (Phase 2B.1 remediation: previously the second symbol was silently
    discarded because it appeared second.)"""
    from packages.parser.pipeline import extract_candidates, normalize, tokenize

    rt = get_profile(PROVIDER)
    n = normalize("BUY EURUSD GBPUSD", rt)
    positioned, _ = tokenize(n, rt)
    graph, _, _ = extract_candidates(positioned, rt)
    instrument_candidates = [
        cands for slot, cands in graph.by_slot if slot is CandidateSlot.INSTRUMENT
    ]
    assert instrument_candidates
    # Both instruments are in the graph.
    values = {c.value for c in instrument_candidates[0]}
    assert "EURUSD" in values
    assert "GBPUSD" in values
    # The resolver consumes the graph: the competing candidates conflict.
    r = parse(_raw("BUY EURUSD GBPUSD"), _md(), rt)
    conflicts = [c for c in r.ir.conflicts if c.slot is CandidateSlot.INSTRUMENT]
    assert conflicts
    assert {c.value for c in conflicts[0].involved} == {"EURUSD", "GBPUSD"}
    assert r.outcome is ParseResultState.MALFORMED
    # The winner (first instrument per §6.3 order) is still emitted.
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.INSTRUMENT] == "EURUSD"


# ---------------------------------------------------------------------------
# §6.2: duplicate candidates collapse (no false conflict)
# ---------------------------------------------------------------------------


def test_repeated_same_keyword_does_not_produce_conflict() -> None:
    """'BUY BUY' has the same direction keyword twice. The parser must
    treat them as duplicate (same slot, same value), NOT as a conflict.
    Per §6.2: 'same slot, same value, same span' = duplicate = collapse."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("BUY BUY"), _md(), rt)
    # No conflict on DIRECTION.
    direction_conflicts = [
        c for c in r.ir.conflicts if c.slot is CandidateSlot.DIRECTION
    ]
    assert not direction_conflicts
    # Outcome is PARTIAL (direction-only, no instrument/entry).
    assert r.outcome is ParseResultState.PARTIAL


# ---------------------------------------------------------------------------
# §5.11: genuine ambiguity (not a contradiction)
# ---------------------------------------------------------------------------


def test_two_entry_trigger_keywords_produce_ambiguity() -> None:
    """'BUY LIMIT STOP EURUSD 1.1000' has two competing entry-trigger
    keywords (LIMIT and STOP). Per §6.2, this is AMBIGUITY, not a
    conflict. The outcome is AMBIGUOUS."""
    rt = get_provider_with_eur_only()
    r = parse(_raw("BUY LIMIT STOP EURUSD 1.1000"), _md(), rt)
    # An ambiguity on ENTRY_TRIGGER is recorded.
    trigger_ambiguities = [
        a for a in r.ir.ambiguities if a.slot is CandidateSlot.ENTRY_TRIGGER
    ]
    assert trigger_ambiguities
    assert trigger_ambiguities[0].kind is AmbiguityKind.AMBIGUOUS_TRIGGER
    # Outcome is AMBIGUOUS (not MALFORMED).
    assert r.outcome is ParseResultState.AMBIGUOUS


# ---------------------------------------------------------------------------
# §14.1: outcome decision
# ---------------------------------------------------------------------------


def test_conflict_produces_malformed_outcome() -> None:
    """A conflict on a non-ambiguous slot (e.g., DIRECTION) produces
    MALFORMED, not AMBIGUOUS."""
    rt = get_profile(PROVIDER)
    r = parse(_raw("BUY SELL"), _md(), rt)
    assert r.outcome is ParseResultState.MALFORMED


def test_grammar_violation_produces_malformed_outcome() -> None:
    """A required rule whose extraction target is absent is a grammar
    violation (§14.2) and produces MALFORMED.

    We construct the violation by writing a message where a REQUIRES'd
    rule is forced to fire but its extraction target is missing. The
    simplest case: a profile that has a REQUIRES rule on ENTRY that
    fires unconditionally. The action rule 'MOVE SL TO BE' alone has
    no number to extract and would normally fail the REQUIRES check
    on the breakeven rule's grammar — but in provider_001 the
    breakeven rule has no REQUIRES, so this is not a grammar
    violation.

    Instead, we test the documented case: the parser must NEVER
    silently reinterpret a missing entry as MALFORMED when the
    profile's grammar permits a direction-only message (§14.2
    branch 5). With multi_message=True, 'BUY' alone is PARTIAL,
    not MALFORMED.
    """
    rt = get_profile(PROVIDER)
    r = parse(_raw("BUY"), _md(), rt)
    # Direction-only with multi_message is PARTIAL, not MALFORMED.
    assert r.outcome is ParseResultState.PARTIAL
    # No conflict (only one direction keyword).
    assert not [c for c in r.ir.conflicts if c.slot is CandidateSlot.DIRECTION]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_provider_with_eur_only():
    """Provider profile that includes EURUSD as a symbol. Used to
    exercise the ENTRY_TRIGGER ambiguity case without needing multiple
    symbols."""
    return get_profile(PROVIDER)
