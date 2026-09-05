"""Contract tests for the Phase 2 parser value objects and concept types.

Covers (per Phase 2A testing brief): construction, required vs optional fields,
immutability/frozen behaviour, SourceSpan validity, SourceMap validity,
raw/normalized mapping invariants, hash/fingerprint separation, and
serialization/equality behaviour. Tests CONTRACTS, not parser behaviour.
"""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from packages.parser import (
    Ambiguity,
    Anchor,
    Candidate,
    CandidateGraph,
    CanonicalParserIR,
    Condition,
    Conflict,
    ContextReference,
    CorrelationRequest,
    EditDelta,
    MatcherSpec,
    MatchEvidence,
    MessageMetadata,
    NormalizedMessage,
    ParsedFragment,
    ParseResult,
    ProviderCapabilities,
    ProviderProfile,
    ProviderRule,
    RawMessage,
    RuleMatch,
    RuleSet,
    ScopeSpec,
    SourceMap,
    SourceSpan,
    Token,
)
from packages.parser.enums import (
    CandidateSlot,
    FragmentState,
    ParseResultState,
)


def _span(start: int, end: int) -> SourceSpan:
    return SourceSpan(start=start, end=end)


def _evidence(kind: str = "rule_match", rule_id: str | None = "r1") -> MatchEvidence:
    return MatchEvidence(kind=kind, rule_id=rule_id, span=_span(0, 3), snippet="BUY")


def _candidate(
    slot: CandidateSlot = CandidateSlot.DIRECTION, value: object = "BUY"
) -> Candidate:
    return Candidate(
        slot=slot,
        value=value,
        source_span=_span(0, 3),
        provenance=(_evidence(),),
    )


def _fragment(
    slot: CandidateSlot = CandidateSlot.DIRECTION, value: object = "BUY"
) -> ParsedFragment:
    return ParsedFragment(
        slot=slot,
        value=value,
        state=FragmentState.RESOLVED,
        evidence=(_evidence(),),
    )


def _ir(**overrides: object) -> CanonicalParserIR:
    defaults: dict[str, object] = {
        "candidates": (),
        "unresolved_fields": (),
        "fragments": (),
        "conflicts": (),
        "ambiguities": (),
        "evidence": (),
        "normalization_decisions": (),
        "conditions": (),
        "provider_id": "provider_alpha",
        "parser_version": "0.1",
    }
    defaults.update(overrides)
    return CanonicalParserIR(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction: required vs optional fields
# ---------------------------------------------------------------------------


def test_match_evidence_optional_fields_default() -> None:
    """MatchEvidence only requires `kind`; the rest default to None/()."""
    evidence = MatchEvidence(kind="rule_match")
    assert evidence.rule_id is None
    assert evidence.span is None
    assert evidence.snippet is None
    assert evidence.fields == ()
    assert evidence.reason is None


def test_required_fields_missing_raises_type_error() -> None:
    """Required dataclass fields cannot be omitted."""
    with pytest.raises(TypeError):
        RawMessage()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        SourceSpan()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Condition()  # type: ignore[call-arg]


def test_normalized_message_requires_source_map() -> None:
    with pytest.raises(TypeError):
        NormalizedMessage()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SourceSpan validity
# ---------------------------------------------------------------------------


def test_source_span_valid() -> None:
    span = SourceSpan(start=0, end=10, source_reference="msg-1")
    assert span.start == 0
    assert span.end == 10
    assert span.source_reference == "msg-1"


def test_source_span_negative_start_rejected() -> None:
    with pytest.raises(ValueError):
        SourceSpan(start=-1, end=3)


def test_source_span_end_before_start_rejected() -> None:
    with pytest.raises(ValueError):
        SourceSpan(start=5, end=2)


def test_source_span_non_int_offsets_rejected() -> None:
    with pytest.raises(TypeError):
        SourceSpan(start="0", end=3)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SourceMap validity
# ---------------------------------------------------------------------------


def test_source_map_valid() -> None:
    smap = SourceMap(char_ranges=((0, 1), (1, 2), (2, 4), (4, 5)))
    assert len(smap.char_ranges) == 4
    assert smap.deleted_ranges == ()


def test_source_map_empty_char_ranges_rejected() -> None:
    with pytest.raises(TypeError):
        SourceMap(char_ranges=[])  # type: ignore[arg-type]


def test_source_map_bad_pair_shape_rejected() -> None:
    with pytest.raises(TypeError):
        SourceMap(char_ranges=((0, 1, 2),))  # type: ignore[arg-type]


def test_source_map_non_int_offsets_rejected() -> None:
    with pytest.raises(TypeError):
        SourceMap(char_ranges=(("0", 1),))  # type: ignore[arg-type]


def test_source_map_empty_raw_range_rejected() -> None:
    with pytest.raises(ValueError):
        SourceMap(char_ranges=((2, 2),))


def test_source_map_non_decreasing_starts_rejected() -> None:
    with pytest.raises(ValueError):
        SourceMap(char_ranges=((5, 6), (0, 1)))


def test_source_map_deleted_ranges_valid_and_ordered() -> None:
    smap = SourceMap(
        char_ranges=((0, 1), (1, 2)),
        deleted_ranges=((2, 3, "strip_zero_width"), (5, 6, "strip_bidi_control")),
    )
    assert smap.deleted_ranges == (
        (2, 3, "strip_zero_width"),
        (5, 6, "strip_bidi_control"),
    )


def test_source_map_deleted_ranges_overlap_rejected() -> None:
    with pytest.raises(ValueError):
        SourceMap(
            char_ranges=((0, 1),),
            deleted_ranges=((0, 5, "strip_zero_width"), (4, 6, "strip_bidi_control")),
        )


def test_source_map_deleted_ranges_empty_op_rejected() -> None:
    with pytest.raises(ValueError):
        SourceMap(char_ranges=((0, 1),), deleted_ranges=((1, 2, ""),))


def test_source_map_deleted_ranges_bad_triple_rejected() -> None:
    with pytest.raises(TypeError):
        SourceMap(char_ranges=((0, 1),), deleted_ranges=((1, 2),))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# raw/normalized mapping invariants (SourceMap.raw_span_for)
# ---------------------------------------------------------------------------


def test_raw_span_for_identity_mapping() -> None:
    smap = SourceMap(char_ranges=((0, 1), (1, 2), (2, 3)))
    assert smap.raw_span_for(0, 3) == (0, 3)
    assert smap.raw_span_for(1, 2) == (1, 2)


def test_raw_span_for_collapsed_whitespace() -> None:
    # raw "ab  cd" -> normalized "ab cd": the two raw spaces collapse to one
    # normalized space whose raw range is (2, 4).
    smap = SourceMap(char_ranges=((0, 1), (1, 2), (2, 4), (4, 5), (5, 6)))
    assert smap.raw_span_for(2, 3) == (2, 4)
    assert smap.raw_span_for(0, 5) == (0, 6)


def test_raw_span_for_nfkc_expansion() -> None:
    # A single raw ligature ("ff" ligature) expands to two normalized chars,
    # both sourced from raw char 0.
    smap = SourceMap(char_ranges=((0, 1), (0, 1)))
    assert smap.raw_span_for(0, 2) == (0, 1)


def test_raw_span_for_rejects_empty_range() -> None:
    smap = SourceMap(char_ranges=((0, 1), (1, 2)))
    with pytest.raises(ValueError):
        smap.raw_span_for(1, 1)


def test_raw_span_for_rejects_out_of_bounds() -> None:
    smap = SourceMap(char_ranges=((0, 1), (1, 2)))
    with pytest.raises(ValueError):
        smap.raw_span_for(0, 3)


def test_normalized_message_enforces_char_ranges_length() -> None:
    with pytest.raises(ValueError):
        NormalizedMessage(
            normalized_text="abc",
            source_map=SourceMap(char_ranges=((0, 1), (1, 2))),  # length 2 != 3
            normalization_decisions=(),
        )


def test_normalized_message_valid() -> None:
    msg = NormalizedMessage(
        normalized_text="ab",
        source_map=SourceMap(char_ranges=((0, 1), (1, 2))),
        normalization_decisions=("collapse_whitespace",),
    )
    assert msg.normalized_text == "ab"
    assert msg.normalization_decisions == ("collapse_whitespace",)


# ---------------------------------------------------------------------------
# Hash / fingerprint field separation
# ---------------------------------------------------------------------------


def test_raw_payload_hash_is_derived_sha256_of_raw_text() -> None:
    raw = RawMessage(
        raw_text="BUY XAUUSD 3330", media_refs=(), raw_payload_hash="ignored"
    )
    assert raw.raw_payload_hash == hashlib.sha256(b"BUY XAUUSD 3330").hexdigest()


def test_raw_payload_hash_ignores_caller_value() -> None:
    a = RawMessage(raw_text="hello", media_refs=(), raw_payload_hash="AAAA")
    b = RawMessage(raw_text="hello", media_refs=(), raw_payload_hash="BBBB")
    assert a.raw_payload_hash == b.raw_payload_hash


def test_raw_payload_hash_changes_with_text() -> None:
    a = RawMessage(raw_text="one", media_refs=(), raw_payload_hash="")
    b = RawMessage(raw_text="two", media_refs=(), raw_payload_hash="")
    assert a.raw_payload_hash != b.raw_payload_hash


def test_raw_payload_hash_distinct_from_canonical_fingerprint() -> None:
    """The message dedup hash and the canonical semantic fingerprint are
    distinct concepts: both are SHA-256 but of different inputs (design §13.3)."""
    from packages.signal_core.domain import canonical_fingerprint

    raw_text = "BUY XAUUSD 3330"
    raw = RawMessage(raw_text=raw_text, media_refs=(), raw_payload_hash="")
    snapshot = (("direction", "BUY"), ("instrument", "XAUUSD"))
    assert raw.raw_payload_hash != canonical_fingerprint(snapshot)


# ---------------------------------------------------------------------------
# Immutability / frozen behaviour
# ---------------------------------------------------------------------------


def test_all_contract_types_are_frozen_dataclasses() -> None:
    types_to_check = [
        SourceSpan,
        SourceMap,
        MatcherSpec,
        Anchor,
        ScopeSpec,
        Condition,
        RawMessage,
        MessageMetadata,
        NormalizedMessage,
        Token,
        MatchEvidence,
        Candidate,
        CandidateGraph,
        RuleMatch,
        Conflict,
        Ambiguity,
        ParsedFragment,
        ContextReference,
        CorrelationRequest,
        EditDelta,
        CanonicalParserIR,
        ParseResult,
        ProviderCapabilities,
        ProviderRule,
        RuleSet,
        ProviderProfile,
    ]
    for cls in types_to_check:
        assert is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        params = getattr(cls, "__dataclass_params__", None)
        assert params is not None and params.frozen, (
            f"{cls.__name__} must be frozen"
        )


def test_frozen_instances_reject_assignment() -> None:
    span = _span(0, 3)
    with pytest.raises(FrozenInstanceError):
        span.start = 1  # type: ignore[misc]


def test_hashability() -> None:
    a = _span(0, 3)
    b = _span(0, 3)
    assert hash(a) == hash(b)
    assert a in {_span(0, 3)}


# ---------------------------------------------------------------------------
# Equality / value semantics
# ---------------------------------------------------------------------------


def test_value_equality() -> None:
    assert _span(0, 3) == _span(0, 3)
    assert _span(0, 3) != _span(0, 4)


def test_raw_message_equality_includes_derived_hash() -> None:
    a = RawMessage(raw_text="x", media_refs=(), raw_payload_hash="")
    b = RawMessage(raw_text="x", media_refs=(), raw_payload_hash="")
    assert a == b
    assert a.raw_payload_hash == b.raw_payload_hash


# ---------------------------------------------------------------------------
# Cross-type wiring smoke tests (construction of a full IR is possible)
# ---------------------------------------------------------------------------


def test_full_ir_and_parse_result_construction() -> None:
    ir = _ir(
        candidates=(_candidate(),),
        fragments=(_fragment(),),
        normalization_decisions=("collapse_whitespace",),
    )
    result = ParseResult(outcome=ParseResultState.PARSED, ir=ir)
    assert result.ir is ir
    assert result.outcome == ParseResultState.PARSED
    assert "outcome" not in {f.name for f in ir.__dataclass_fields__.values()}
