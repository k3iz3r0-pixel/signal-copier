"""Normalization + tokenization behaviour tests (design §5.5.1).

Verifies the deterministic normalization pipeline:

- step 1: strip_control_only (zero-width + bidi)
- step 2: NFKC
- step 3: strip_markdown
- step 4: collapse_whitespace
- step 5: canonicalize_separators
- step 6: repetition truncation (adversarial)

Plus SourceMap invariant checks: raw spans always trace to the original
raw characters via SourceMap.raw_span_for.
"""

from __future__ import annotations

from packages.parser.enums import TokenCategory
from packages.parser.pipeline import normalize, tokenize
from packages.parser.types import RawMessage
from tests.parser._helpers import make_runtime


def _norm_tokens(text: str, provider: str = "provider_001"):
    rt = make_runtime(provider)
    norm = normalize(text, rt)
    positioned, violations = tokenize(norm, rt)
    return norm, positioned, violations


def test_normalize_pure_keeps_text() -> None:
    """Pure ASCII input is unchanged; no decisions recorded."""
    norm, _, _ = _norm_tokens("BUY EURUSD 1.1000")
    assert norm.normalized_text == "BUY EURUSD 1.1000"
    assert norm.normalization_decisions == ()


def test_normalize_strips_zero_width() -> None:
    """U+200B zero-width space is removed; raw span recorded."""
    norm, _, _ = _norm_tokens("BUY\u200b EURUSD 1.1000")
    assert norm.normalized_text == "BUY EURUSD 1.1000"
    assert "strip_zero_width" in norm.normalization_decisions


def test_normalize_strips_bidi_control() -> None:
    """Bidi control characters are removed."""
    norm, _, _ = _norm_tokens("\u202aBUY EURUSD 1.1000")
    assert "\u202a" not in norm.normalized_text
    assert "strip_bidi_control" in norm.normalization_decisions


def test_normalize_nfkc_expansion() -> None:
    """NFKC normalizes compatible characters (fullwidth -> ASCII)."""
    norm, _, _ = _norm_tokens("\uff22\uff35\uff39 EURUSD")  # fullwidth BUY
    assert norm.normalized_text == "BUY EURUSD"
    assert "nfkc" in norm.normalization_decisions


def test_normalize_collapses_whitespace_runs() -> None:
    norm, _, _ = _norm_tokens("BUY    EURUSD\t1.1000")
    assert "  " not in norm.normalized_text
    assert "collapse_whitespace" in norm.normalization_decisions


def test_normalize_strips_markdown() -> None:
    norm, _, _ = _norm_tokens("**BUY** EURUSD 1.1000")
    assert "**" not in norm.normalized_text
    assert "strip_markdown" in norm.normalization_decisions


def test_normalize_canonicalizes_separators() -> None:
    """provider_002 declares em-dash as the canonical separator; the em-dash
    itself is the canonical form, so it stays unchanged. To prove
    canonicalization works, give it an en-dash variant which must be
    converted to em-dash."""
    norm, _, _ = _norm_tokens("SL \u2013 1.0950", provider="provider_002")  # en-dash
    assert "\u2014" in norm.normalized_text  # canonicalized to em-dash
    assert "\u2013" not in norm.normalized_text
    assert "separator_canonicalization" in norm.normalization_decisions


def test_normalize_repetition_truncation() -> None:
    """Long runs of the same character are bounded."""
    huge = "A" * 5000
    norm, _, _ = _norm_tokens(huge)
    assert len(norm.normalized_text) < 5000
    assert "repetition_truncation" in norm.normalization_decisions


def test_source_map_raw_span_for_round_trip() -> None:
    """Normalized offsets project back to contiguous raw offsets."""
    norm, _, _ = _norm_tokens("BUY  EURUSD  1.1000")
    raw_text = "BUY  EURUSD  1.1000"
    for i in range(len(norm.normalized_text)):
        s, e = norm.source_map.raw_span_for(i, i + 1)
        assert 0 <= s < e <= len(raw_text)
        assert raw_text[s:e].replace(" ", "") == norm.normalized_text[i].replace(" ", ""), (
            f"raw[{s}:{e}]={raw_text[s:e]!r} != norm[{i}]={norm.normalized_text[i]!r}"
        )


def test_tokens_classify_numbers_keywords_symbols() -> None:
    """NUMBER, KEYWORD, SYMBOL, WHITESPACE categories are produced."""
    _, positioned, _ = _norm_tokens("BUY EURUSD 1.1000")
    cats = [tok.category for _, _, tok in positioned]
    assert TokenCategory.KEYWORD in cats
    assert TokenCategory.SYMBOL in cats
    assert TokenCategory.NUMBER in cats
    assert TokenCategory.WHITESPACE in cats


def test_token_source_spans_are_raw_offsets() -> None:
    """Every token's source_span points into the ORIGINAL raw_text."""
    raw_text = "BUY EURUSD 1.1000"
    _norm, positioned, _ = _norm_tokens(raw_text)
    for _, _, tok in positioned:
        s, e = tok.source_span.start, tok.source_span.end
        assert 0 <= s < e <= len(raw_text)
        assert raw_text[s:e] == tok.text


def test_normalize_rejects_message_too_long() -> None:
    """Messages beyond max_message_length are rejected (no raw truncation)."""
    rt = make_runtime("provider_001")
    huge = "x" * (rt.profile.max_message_length + 1)
    from packages.parser.pipeline import _NormalizationRejected

    try:
        normalize(huge, rt)
    except _NormalizationRejected as rejected:
        assert rejected.code == "message_too_long"
    else:
        raise AssertionError("expected _NormalizationRejected")


def test_normalize_rejects_embedded_control_char() -> None:
    """Raw control characters other than \\t \\n \\r are rejected."""
    from packages.parser.pipeline import _NormalizationRejected

    try:
        _norm_tokens("BUY\x01 EURUSD")
    except _NormalizationRejected as rejected:
        assert rejected.code == "embedded_control_char"
    else:
        raise AssertionError("expected _NormalizationRejected")


def test_normalize_preserves_raw_unmutated() -> None:
    """The RawMessage.raw_text is never mutated by the pipeline."""
    original = "BUY\u200b EURUSD"
    raw = RawMessage(raw_text=original, media_refs=(), raw_payload_hash="")
    rt = make_runtime("provider_001")
    norm = normalize(raw.raw_text, rt)
    assert raw.raw_text == original
    assert norm.normalized_text != original


def test_tokenize_no_numeric_overflow_when_within_limit() -> None:
    """Small numbers don't trigger the digit-run overflow violation."""
    _, _, violations = _norm_tokens("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100")
    assert all(v.kind != "numeric_overflow" for v in violations)