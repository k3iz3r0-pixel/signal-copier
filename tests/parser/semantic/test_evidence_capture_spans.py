"""Captured-group source span regression tests (Phase 2B.1 remediation).

The audit found that regex evidence spans could cover the whole match
rather than the actual captured semantic value (e.g. "SL — 1.0950" as
evidence for the SL value 1.0950).

After the remediation, the site VALUE span (and therefore the candidate's
SourceSpan and its provenance evidence) is the captured group's span in
normalized coordinates projected to the exact raw characters of the
extracted value. The whole-match span is retained separately for the
§7.3 rule-overlap precedence (RuleMatch.span).
"""

from __future__ import annotations

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.parser.pipeline import normalize, tokenize
from tests.parser._helpers import make_metadata, make_raw, make_runtime


def _fragment(result, slot: CandidateSlot):
    for fragment in result.ir.fragments:
        if fragment.slot is slot:
            return fragment
    raise AssertionError(f"no fragment for slot {slot}")


def _candidate_for_value(result, slot: CandidateSlot, text: str):
    for candidate in result.ir.candidates:
        if candidate.slot is slot and str(candidate.value) == text:
            return candidate
    raise AssertionError(f"no {slot} candidate with value {text!r}")


def test_regex_capture_span_points_at_captured_value_p002_sl() -> None:
    """p002's em-dash SL regex captures the NUMBER; the SL candidate span
    must be exactly the raw characters of 1.0950, not "SL — 1.0950"."""
    raw = "BUY EURUSD\nENTRY 1.1000\nSL — 1.0950\nTP — 1.1100"
    r = parse(
        make_raw(raw), make_metadata("provider_002"), make_runtime("provider_002")
    )
    assert r.outcome is ParseResultState.PARSED
    sl = _fragment(r, CandidateSlot.SL)
    expected = raw.index("1.0950")
    span = sl.evidence[0].span
    assert span is not None
    assert (span.start, span.end) == (expected, expected + len("1.0950"))
    assert raw[span.start : span.end] == "1.0950"


def test_regex_capture_span_points_at_captured_value_p002_tp() -> None:
    raw = "BUY EURUSD\nENTRY 1.1000\nSL — 1.0950\nTP — 1.1100"
    r = parse(
        make_raw(raw), make_metadata("provider_002"), make_runtime("provider_002")
    )
    tp = _fragment(r, CandidateSlot.TP)
    expected = raw.index("1.1100")
    span = tp.evidence[0].span
    assert span is not None
    assert (span.start, span.end) == (expected, expected + len("1.1100"))
    assert raw[span.start : span.end] == "1.1100"


def test_action_capture_span_points_at_captured_number() -> None:
    """'CHANGE TP TO 1.1150' — the MOVE_TP action evidence must point at
    the captured number, not at the whole phrase."""
    raw = "CHANGE TP TO 1.1150"
    r = parse(
        make_raw(raw), make_metadata("provider_001"), make_runtime("provider_001")
    )
    assert r.outcome is ParseResultState.PARSED
    action = _fragment(r, CandidateSlot.ACTION)
    expected = raw.index("1.1150")
    capture_spans = [
        ev.span
        for ev in action.evidence
        if ev.span is not None and raw[ev.span.start : ev.span.end] == "1.1150"
    ]
    assert capture_spans, "no evidence span pointing at the captured value"
    for span in capture_spans:
        assert (span.start, span.end) == (expected, expected + len("1.1150"))


def test_condition_capture_span_points_at_captured_number() -> None:
    raw = "BUY EURUSD AT 1.1000 SL 1.0950 TP 1.1100"
    r = parse(
        make_raw(raw), make_metadata("provider_001"), make_runtime("provider_001")
    )
    condition = _fragment(r, CandidateSlot.CONDITION)
    expected = raw.index("1.1000")
    span = condition.evidence[0].span
    assert span is not None
    assert raw[span.start : span.end] == "1.1000"
    assert (span.start, span.end) == (expected, expected + len("1.1000"))


def test_capture_span_matches_candidate_source_span() -> None:
    """The candidate's SourceSpan and its rule_match evidence span agree."""
    raw = "CHANGE TP TO 1.1150"
    r = parse(
        make_raw(raw), make_metadata("provider_001"), make_runtime("provider_001")
    )
    candidate = _candidate_for_value(r, CandidateSlot.ACTION, "InstructionType.MOVE_TP")
    rule_match_spans = [
        ev.span for ev in candidate.provenance if ev.kind == "rule_match"
    ]
    assert rule_match_spans
    for span in rule_match_spans:
        assert (span.start, span.end) == (
            candidate.source_span.start,
            candidate.source_span.end,
        )
        assert raw[span.start : span.end] == "1.1150"


def test_capture_spans_survive_normalization_offset_shift() -> None:
    """Raw/normalized offset mapping stays intact: with characters stripped
    BEFORE the capture, the raw span still points at the exact raw value."""
    raw = "BUY**\u200b EURUSD AT 1.1000 SL 1.0950 TP 1.1100"
    r = parse(
        make_raw(raw), make_metadata("provider_001"), make_runtime("provider_001")
    )
    condition = _fragment(r, CandidateSlot.CONDITION)
    span = condition.evidence[0].span
    assert span is not None
    assert raw[span.start : span.end] == "1.1000"


def test_whole_match_span_kept_for_overlap_precedence() -> None:
    """RuleMatch.span (§7.3 precedence input) is the whole-match span for
    regex rules; the capture span is the candidate value span. In
    'CLOSE 50%' the percent close rule's longer MATCH span outranks the
    plain CLOSE keyword so no false conflict occurs."""
    raw = "CLOSE 50%"
    r = parse(
        make_raw(raw), make_metadata("provider_001"), make_runtime("provider_001")
    )
    assert r.outcome is ParseResultState.PARSED
    assert not r.ir.conflicts
    action = _fragment(r, CandidateSlot.ACTION)
    assert action.value.name == "PARTIAL_CLOSE"


def test_empty_capture_does_not_crash_binding() -> None:
    """An optional group that captures nothing is skipped, not bound to an
    empty value."""
    raw = "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100"
    rt = make_runtime("provider_001")
    norm = normalize(raw, rt)
    positioned, _ = tokenize(norm, rt)
    assert positioned  # sanity: pipeline stages run
    r = parse(make_raw(raw), make_metadata("provider_001"), rt)
    assert r.outcome is ParseResultState.PARSED
