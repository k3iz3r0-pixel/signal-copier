"""Parser semantic behaviour tests (design §6, §7, §14).

Covers the candidate graph, rule evaluation, semantic resolution, fragment
emission, conflict/ambiguity handling, and outcome decision procedure.

Each test runs the full pipeline against a known input and asserts on the
resulting ParseResult (outcome + fragments + evidence).
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal

import pytest

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    MessageEvent,
    ParseResultState,
)
from packages.parser.types import (
    NormalizedMessage,
    SourceMap,
)
from packages.signal_core.enums import EntryTrigger, TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime


def _go(provider: str, text: str, event: MessageEvent = MessageEvent.CREATE):
    rt = make_runtime(provider)
    return parse(make_raw(text), make_metadata(provider, event), rt)


# ---------------------------------------------------------------------------
# Normal signal
# ---------------------------------------------------------------------------


def test_simple_buy_parsed() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by_slot[CandidateSlot.INSTRUMENT] == "EURUSD"
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal("1.1000"))
    assert by_slot[CandidateSlot.SL] == Price(Decimal("1.0950"))
    assert by_slot[CandidateSlot.TP] == (Price(Decimal("1.1100")),)


def test_simple_sell_parsed() -> None:
    r = _go("provider_001", "SELL EURUSD 1.2500 SL 1.2550 TP 1.2400")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by_slot[CandidateSlot.INSTRUMENT] == "EURUSD"


def test_multiple_tp_levels_preserved() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 TP 1.1150")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.TP] == (
        Price(Decimal("1.1100")),
        Price(Decimal("1.1150")),
    )


def test_entry_range_resolves_to_geometry_range() -> None:
    r = _go("provider_001", "BUY XAUUSD 2350-2360 SL 2340 TP 2400")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_GEOMETRY].name == "RANGE"
    assert by_slot[CandidateSlot.ENTRY].low == Price(Decimal(2350))
    assert by_slot[CandidateSlot.ENTRY].high == Price(Decimal(2360))


def test_pending_order_with_limit_trigger() -> None:
    r = _go("provider_001", "BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_TRIGGER] is EntryTrigger.LIMIT


def test_pending_order_with_stop_trigger() -> None:
    r = _go("provider_001", "BUY STOP EURUSD 1.1000 SL 1.0950 TP 1.1100")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_TRIGGER] is EntryTrigger.STOP


def test_long_short_canonicalized_to_buy_sell() -> None:
    """provider_003 uses LONG/SHORT keywords; canonical param maps them."""
    r = _go("provider_003", "LONG BTC 60000 SL 58000 TP 65000")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by_slot[CandidateSlot.INSTRUMENT] == "BTC"
    # Raw text is preserved as evidence (canonical_alias).
    has_canonical_evidence = any(
        any(ev.kind == "canonical_alias" for ev in f.evidence)
        for f in r.ir.fragments
    )
    assert has_canonical_evidence


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def test_close_emits_action_fragment() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100\nCLOSE")
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert len(actions) == 1
    assert actions[0].value.name == "CLOSE"


def test_close_half_emits_partial_close() -> None:
    r = _go("provider_001", "CLOSE HALF")
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions[0].value.name == "PARTIAL_CLOSE"


def test_close_percent_emits_partial_close() -> None:
    r = _go("provider_001", "CLOSE 50%")
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions[0].value.name == "PARTIAL_CLOSE"


def test_remove_sl_emits_move_sl() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100\nREMOVE SL")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions[0].value.name == "MOVE_SL"


def test_cancel_pending_emits_cancel() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100\nCANCEL PENDING")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions[0].value.name == "CANCEL"


def test_trigger_pending_emits_modify() -> None:
    """Per design §8.1 open-question resolution: TRIGGER_PENDING is MODIFY."""
    r = _go("provider_001", "TRIGGER PENDING NOW")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions[0].value.name == "MODIFY"


def test_breakeven_phrase_emits_breakeven() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950\nMOVE SL TO BE")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions[0].value.name == "BREAKEVEN"


def test_action_suppresses_signal_entry_fragment() -> None:
    """A '50' inside 'CLOSE 50%' must NOT be emitted as ENTRY=50."""
    r = _go("provider_001", "CLOSE 50%")
    entries = [f for f in r.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert all(f.value != Price(Decimal(50)) for f in entries)


def test_change_tp_emits_move_tp() -> None:
    """'CHANGE TP TO 1.1150' as a standalone action emits ACTION=MOVE_TP.
    The rule fires only when no direction keyword is present (FORBIDS),
    so the message must not also contain BUY/SELL/LONG/SHORT."""
    r = _go("provider_001", "CHANGE TP TO 1.1150")
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert any(a.value.name == "MOVE_TP" for a in actions)


def test_action_message_correlation_request() -> None:
    """Actions targeting the last signal produce TARGET_LAST_SIGNAL."""
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100\nCLOSE")
    assert r.ir.correlation_request is not None
    assert r.ir.correlation_request.kind.name == "TARGET_LAST_SIGNAL"


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------


def test_direction_only_yields_partial_when_multi_message() -> None:
    """provider_001 has multi_message=True, so 'BUY' alone -> PARTIAL."""
    r = _go("provider_001", "BUY")
    assert r.outcome is ParseResultState.PARTIAL
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert CandidateSlot.ENTRY in r.ir.unresolved_fields


def test_empty_message_yields_no_signal() -> None:
    r = _go("provider_001", "")
    assert r.outcome is ParseResultState.NO_SIGNAL


def test_chat_text_yields_no_signal() -> None:
    r = _go("provider_001", "hello everyone how are you today")
    assert r.outcome is ParseResultState.NO_SIGNAL


def test_deleted_message_emits_delete_apply_correlation() -> None:
    r = _go("provider_001", "anything", event=MessageEvent.DELETE)
    assert r.outcome is ParseResultState.NO_SIGNAL
    assert r.ir.correlation_request is not None
    assert r.ir.correlation_request.kind.name == "DELETE_APPLY"
    assert any(ev.kind == "message_deleted" for ev in r.ir.evidence)


def test_edited_message_emits_edit_apply_correlation() -> None:
    """An EDIT event with REPARSE_DELTA behavior emits EDIT_APPLY."""
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100", event=MessageEvent.EDIT)
    assert r.ir.correlation_request is not None
    assert r.ir.correlation_request.kind.name == "EDIT_APPLY"


def test_edit_with_ignore_behavior_yields_no_signal() -> None:
    """If a profile declares IGNORE for edits, an EDIT is NO_SIGNAL."""
    from packages.parser import ProviderCapabilities, ProviderProfile, RuleSet
    from packages.parser.enums import (
        DeleteBehavior,
        EditBehavior,
        FollowUpBehavior,
        ReplyRequirement,
    )
    from packages.signal_core.enums import SourceType

    caps = ProviderCapabilities(
        close_full=False, close_half=False, profit_close=False,
        move_sl_breakeven=False, remove_sl=False, cancel_pending=False,
        trigger_pending=False, move_sl_number=False, move_sl_conditional=False,
        move_tp_conditional=False, move_entry_conditional=False,
        edit_handling=False, delete_handling=False, reply_required=False,
        negative_keywords=False, last_signal_execution=False, trailing=False,
        multi_signal=False, multi_message=False,
    )
    profile = ProviderProfile(
        provider_name="ignore_edits",
        capabilities=caps,
        rule_set=RuleSet(rules=()),
        symbol_aliases=(),
        tokenizer_pattern="",
        field_separators=(),
        multi_value_separators=(),
        decimal_format="dot",
        range_patterns=(),
        multiline_mode=False,
        reply_requirement=ReplyRequirement.NONE,
        edit_behavior=EditBehavior.IGNORE,
        delete_behavior=DeleteBehavior.CANCEL_TARGET,
        follow_up_behavior=FollowUpBehavior.TARGET_LAST_SIGNAL,
        version="2B",
    )
    from datetime import datetime

    from packages.parser import ProfileRuntime, parse
    from packages.parser.enums import MessageEvent
    from packages.parser.types import MessageMetadata, RawMessage

    rt = ProfileRuntime(
        profile=profile,
        effective_rules=(),
        tokenizer=None,
        rule_patterns={},
        number_pattern=None,
        symbol_table={},
        keyword_texts=(),
        override_pairs=(),
    )
    raw = RawMessage(raw_text="BUY EURUSD 1.1000", media_refs=(), raw_payload_hash="")
    md = MessageMetadata(
        provider_name="ignore_edits",
        source_type=SourceType.TELEGRAM,
        timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        message_event=MessageEvent.EDIT,
    )
    r = parse(raw, md, rt)
    assert r.outcome is ParseResultState.NO_SIGNAL


# ---------------------------------------------------------------------------
# §7.3 overlap precedence
# ---------------------------------------------------------------------------


def test_range_rule_outranks_single_number_for_entry() -> None:
    """'2350-2360' should be the entry, not '2350' (range wins by §7.3)."""
    r = _go("provider_001", "BUY XAUUSD 2350-2360 SL 2340 TP 2400")
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY_GEOMETRY].name == "RANGE"
    assert r.ir.conflicts == ()


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def test_normalization_decisions_propagated_to_ir() -> None:
    """When a normalization op fires, the IR records it."""
    r = _go("provider_001", "BUY\u200b EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert "strip_zero_width" in r.ir.normalization_decisions


def test_evidence_captures_rule_id() -> None:
    """Every rule-bound fragment carries its rule_id in evidence."""
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    rule_ids = set()
    for f in r.ir.fragments:
        for ev in f.evidence:
            if ev.rule_id is not None:
                rule_ids.add(ev.rule_id)
    assert "p001.direction.buy" in rule_ids
    assert "common.sl.number" in rule_ids


# ---------------------------------------------------------------------------
# SourceMap invariant on token spans
# ---------------------------------------------------------------------------


def test_all_token_spans_are_raw_offsets() -> None:
    """No token or fragment source_span may exceed len(raw_text)."""
    text = "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100"
    r = _go("provider_001", text)
    raw_len = len(text)
    for f in r.ir.fragments:
        if f.evidence:
            for ev in f.evidence:
                if ev.span is not None:
                    assert ev.span.start >= 0
                    assert ev.span.end <= raw_len
                    assert ev.span.start < ev.span.end


def test_token_text_matches_raw_extraction() -> None:
    """Each non-whitespace token's text equals raw_text[span.start:span.end].

    Whitespace tokens are excluded: the normalization collapses multiple raw
    spaces into one canonical space whose source_span covers the entire
    original run, so the token text (' ') is a strict substring of the raw
    span text.
    """
    from packages.parser.enums import TokenCategory
    from packages.parser.pipeline import normalize, tokenize

    text = "BUY  EURUSD  1.1000"
    rt = make_runtime("provider_001")
    norm = normalize(text, rt)
    positioned, _ = tokenize(norm, rt)
    for _, _, tok in positioned:
        if tok.category is TokenCategory.WHITESPACE:
            continue
        s, e = tok.source_span.start, tok.source_span.end
        assert text[s:e] == tok.text, (
            f"raw[{s}:{e}]={text[s:e]!r} != token text {tok.text!r}"
        )


# ---------------------------------------------------------------------------
# Smoke for malformed / unsupported grammar
# ---------------------------------------------------------------------------


def test_grammar_violation_missing_number_emits_malformed() -> None:
    """A provider whose SL rule has REQUIRED sees 'SL' alone as MALFORMED."""
    from packages.parser import (
        Anchor,
        MatcherSpec,
        ProviderCapabilities,
        ProviderProfile,
        ProviderRule,
        RuleSet,
        ScopeSpec,
    )
    from packages.parser.enums import (
        Constraint,
        DeleteBehavior,
        EditBehavior,
        FollowUpBehavior,
        MatcherKind,
        OccurrenceSelection,
        ReplyRequirement,
        ScopeKind,
        SemanticTarget,
    )
    from packages.signal_core.enums import SourceType

    sl_required = ProviderRule(
        id="custom.sl.required",
        category="SL",
        matcher=MatcherSpec(kind=MatcherKind.NUMBER),
        scope=ScopeSpec(
            kind=ScopeKind.AFTER_TOKEN,
            anchors=(Anchor(text="SL"),),
        ),
        constraints=(Constraint.REQUIRED,),
        target=SemanticTarget.SL,
        priority=10,
        occurrence=OccurrenceSelection.FIRST,
    )
    profile = ProviderProfile(
        provider_name="strict_provider",
        capabilities=ProviderCapabilities(
            close_full=False, close_half=False, profit_close=False,
            move_sl_breakeven=False, remove_sl=False, cancel_pending=False,
            trigger_pending=False, move_sl_number=False, move_sl_conditional=False,
            move_tp_conditional=False, move_entry_conditional=False,
            edit_handling=False, delete_handling=False, reply_required=False,
            negative_keywords=False, last_signal_execution=False, trailing=False,
            multi_signal=False, multi_message=False,
        ),
        rule_set=RuleSet(rules=(sl_required,)),
        symbol_aliases=(),
        tokenizer_pattern="",
        field_separators=(),
        multi_value_separators=(),
        decimal_format="dot",
        range_patterns=(),
        multiline_mode=False,
        reply_requirement=ReplyRequirement.NONE,
        edit_behavior=EditBehavior.REPARSE_DELTA,
        delete_behavior=DeleteBehavior.CANCEL_TARGET,
        follow_up_behavior=FollowUpBehavior.TARGET_LAST_SIGNAL,
        version="2B",
    )
    from datetime import datetime

    from packages.parser import ProfileRuntime, parse
    from packages.parser.types import MessageMetadata, RawMessage

    rt = ProfileRuntime(
        profile=profile,
        effective_rules=(sl_required,),
        tokenizer=__import__("re").compile(r"\d+|[A-Za-z]+|\s|[^\sA-Za-z0-9]"),
        rule_patterns={},
        number_pattern=__import__("re").compile(r"\d{1,13}(?:\.\d{1,12})?"),
        symbol_table={},
        keyword_texts=("SL",),
        override_pairs=(),
    )
    raw = RawMessage(raw_text="SL", media_refs=(), raw_payload_hash="")
    md = MessageMetadata(
        provider_name="strict_provider",
        source_type=SourceType.TELEGRAM,
        timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        message_event=MessageEvent.CREATE,
    )
    r = parse(raw, md, rt)
    assert r.outcome is ParseResultState.MALFORMED
    assert any(ev.kind == "grammar_violation_missing_number" for ev in r.ir.evidence)


# ---------------------------------------------------------------------------
# Conflict detection (competing non-compatible interpretations)
# ---------------------------------------------------------------------------


def test_ir_carries_no_outcome_field() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert "outcome" not in r.ir.__dataclass_fields__


def test_parse_result_is_immutable() -> None:
    r = _go("provider_001", "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        r.outcome = ParseResultState.NO_SIGNAL  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helper dataclass sanity
# ---------------------------------------------------------------------------


def test_normalized_message_length_mismatch_rejected() -> None:
    """NormalizedMessage enforces char_ranges length == normalized_text length."""
    with pytest.raises(ValueError):
        NormalizedMessage(
            normalized_text="abc",
            source_map=SourceMap(char_ranges=((0, 1), (1, 2))),  # 2 != 3
            normalization_decisions=(),
        )