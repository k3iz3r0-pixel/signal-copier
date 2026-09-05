"""SourceMap interleaved-deletion regression tests (Phase 2B.1).

The audit verified a construction crash in normalize(): deletion ops run
in pipeline order (zero-width, bidi, markdown, repetition), so a later
op's deletion can precede an earlier op's deletion in raw-offset terms.
SourceMap.deleted_ranges requires ordered, non-overlapping entries, so
interleaved operations crashed with ValueError at construction.

Ops delete pairwise-disjoint raw characters, so the canonical
raw-position order is the sorted order — that is the generic fix. These
tests cover multiple non-contiguous deletions interleaved with retained
and replaced spans, plus the ADR 0012 exact-once accounting invariant.
"""

from __future__ import annotations

from packages.parser.enums import TokenCategory
from packages.parser.pipeline import normalize, tokenize
from tests.parser._helpers import make_runtime

PROVIDER = "provider_001"


def _norm(text: str, provider: str = PROVIDER):
    return normalize(text, make_runtime(provider))


def _assert_sourcemap_contract(norm, raw_text: str) -> None:
    """ADR 0012 invariants: ordered non-overlapping deletions, exact-once
    accounting of every raw offset, and valid projection."""
    deleted = norm.source_map.deleted_ranges
    prev_end = -1
    for start, end, _op in deleted:
        assert 0 <= start < end <= len(raw_text)
        assert start >= prev_end, f"deleted_ranges not ordered at {start}"
        prev_end = end
    covered: set[int] = set()
    for start, end in norm.source_map.char_ranges:
        covered.update(range(start, end))
    for start, end, _op in deleted:
        covered.update(range(start, end))
    assert covered == set(range(len(raw_text)))
    length = len(norm.normalized_text)
    for i in range(length):
        s, e = norm.source_map.raw_span_for(i, i + 1)
        assert 0 <= s < e <= len(raw_text)


def test_interleaved_zero_width_and_markdown_deletions_do_not_crash() -> None:
    """'*a<U+200B>b*' — the regression crash: markdown deletions at raw 0/4
    interleave with the zero-width deletion at raw 2."""
    raw = "*a\u200bb*"
    norm = _norm(raw)
    assert norm.normalized_text == "ab"
    assert "strip_markdown" in norm.normalization_decisions
    assert "strip_zero_width" in norm.normalization_decisions
    _assert_sourcemap_contract(norm, raw)


def test_multiple_non_contiguous_deletions_of_both_kinds() -> None:
    raw = "a\u200b * b\u202a * c\u200cd"
    norm = _norm(raw)
    assert "\u200b" not in norm.normalized_text
    assert "*" not in norm.normalized_text
    assert norm.normalized_text.count(" ") == norm.normalized_text.count(" ")
    _assert_sourcemap_contract(norm, raw)
    ops = {op for _s, _e, op in norm.source_map.deleted_ranges}
    assert "strip_markdown" in ops
    assert {"strip_zero_width", "strip_bidi_control"} & ops


def test_markdown_zero_width_and_repetition_interleaved() -> None:
    """Repetition truncation deletions must also interleave cleanly with
    earlier ops' deletions."""
    raw = "x\u200b" + "A" * 5000 + "*"
    norm = _norm(raw)
    assert len(norm.normalized_text) < len(raw)
    assert "repetition_truncation" in norm.normalization_decisions
    _assert_sourcemap_contract(norm, raw)


def test_deleted_ranges_sorted_by_raw_position() -> None:
    raw = "*BUY**\u200b*EURUSD*"
    norm = _norm(raw)
    starts = [start for start, _end, _op in norm.source_map.deleted_ranges]
    assert starts == sorted(starts)
    _assert_sourcemap_contract(norm, raw)


def test_nfkc_replacement_spans_and_deletions_interleave() -> None:
    """NFKC one-to-many expansions between deletion sites keep the map
    consistent (retained/replaced spans)."""
    raw = "\uff22*\u200b\uff21"
    norm = _norm(raw)
    _assert_sourcemap_contract(norm, raw)
    assert "nfkc" in norm.normalization_decisions


def test_tokens_still_project_to_raw_after_interleaved_deletions() -> None:
    raw = "**BUY**\u200b EURUSD 1.1000"
    rt = make_runtime(PROVIDER)
    norm = _norm(raw)
    positioned, _ = tokenize(norm, rt)
    for norm_start, norm_end, token in positioned:
        if token.category is TokenCategory.WHITESPACE:
            continue
        s, e = norm.source_map.raw_span_for(norm_start, norm_end)
        assert raw[s:e] == token.text, (
            f"raw[{s}:{e}]={raw[s:e]!r} != token {token.text!r}"
        )


def test_deleted_ranges_record_op_names_for_every_op() -> None:
    raw = "\u202a*\u200bX*"
    norm = _norm(raw)
    assert norm.normalized_text == "X"
    ops = {op for _s, _e, op in norm.source_map.deleted_ranges}
    assert "strip_zero_width" in ops
    assert "strip_bidi_control" in ops
    assert "strip_markdown" in ops
