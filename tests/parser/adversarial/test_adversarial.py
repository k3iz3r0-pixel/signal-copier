"""Adversarial parser tests (design §15, §16).

Covers:
- static regex safety (`check_pattern_safe`) — backreferences,
  lookbehind, nested unbounded quantifiers, over-long patterns;
- bounded input — message_too_long, embedded_control_char,
  zero-width-only, bidi-control-only;
- bounded counts — numeric overflow, candidate/match limit
  (unit-level checks on the constants);
- Unicode edge cases — emoji, combined marks;
- pathological repetition.
"""

from __future__ import annotations

from datetime import UTC

import pytest

from packages.parser.enums import ParseResultState
from packages.parser.pipeline import _NormalizationRejected, normalize
from packages.parser.safety import (
    MAX_CANDIDATES,
    MAX_DIGIT_RUN,
    MAX_NUMERIC_TOKENS_PER_FIELD,
    MAX_NUMERIC_TOKENS_PER_MESSAGE,
    MAX_PATTERN_LENGTH,
    MAX_RULE_MATCHES,
    REPETITION_RUN_LIMIT,
    UnsafePatternError,
    check_pattern_safe,
    compile_safe,
)
from tests.parser._helpers import make_metadata, make_raw, make_runtime

# ---------------------------------------------------------------------------
# Static regex safety
# ---------------------------------------------------------------------------


def test_unsafe_pattern_backreference_rejected() -> None:
    with pytest.raises(UnsafePatternError):
        check_pattern_safe(r"(a)\1")


def test_unsafe_pattern_lookbehind_rejected() -> None:
    with pytest.raises(UnsafePatternError):
        check_pattern_safe(r"(?<=a)b")


def test_unsafe_pattern_nested_unbounded_quantifier_rejected() -> None:
    with pytest.raises(UnsafePatternError):
        check_pattern_safe(r"(a+)+")


def test_unsafe_pattern_overlong_rejected() -> None:
    with pytest.raises(UnsafePatternError):
        check_pattern_safe(r"a" * (MAX_PATTERN_LENGTH + 1))


def test_safe_pattern_compiles() -> None:
    p = compile_safe(r"\d{1,13}(?:\.\d{1,12})?")
    assert p.match("1.1000") is not None


def test_safe_pattern_word_boundary() -> None:
    p = compile_safe(r"\bAT\s+(\d+)")
    assert p.search("AT 1.1100") is not None


# ---------------------------------------------------------------------------
# Bounded input (static check, NOT wall-clock)
# ---------------------------------------------------------------------------


def test_oversized_message_is_malformed() -> None:
    rt = make_runtime("provider_001")
    big = "A" * (rt.profile.max_message_length + 1)
    with pytest.raises(_NormalizationRejected) as info:
        normalize(big, rt)
    assert info.value.code == "message_too_long"


def test_embedded_control_char_rejected() -> None:
    rt = make_runtime("provider_001")
    with pytest.raises(_NormalizationRejected) as info:
        normalize("BUY\x07 EURUSD", rt)
    assert info.value.code == "embedded_control_char"


def test_zero_width_only_message_rejected() -> None:
    rt = make_runtime("provider_001")
    with pytest.raises(_NormalizationRejected) as info:
        normalize("\u200b\u200c", rt)
    assert info.value.code == "zero_width_only"


def test_bidi_only_message_rejected() -> None:
    rt = make_runtime("provider_001")
    with pytest.raises(_NormalizationRejected) as info:
        normalize("\u202a\u202b", rt)
    assert info.value.code == "bidi_control_only"


def test_whitespace_collapse_keeps_one_space() -> None:
    """Whitespace runs collapse to a single U+0020; the message is not
    rejected as 'empty_after_normalization' because at least one char
    survives."""
    rt = make_runtime("provider_001")
    norm = normalize("     ", rt)
    assert norm.normalized_text == " "
    assert "collapse_whitespace" in norm.normalization_decisions


def test_tab_newline_carriage_allowed_in_raw() -> None:
    """Only tab, newline, carriage return are permitted control chars."""
    rt = make_runtime("provider_001")
    norm = normalize("BUY\nEURUSD\t1.1000\r\nSL 1.0950", rt)
    assert "EURUSD" in norm.normalized_text


# ---------------------------------------------------------------------------
# Bounded counts (constant-level invariants)
# ---------------------------------------------------------------------------


def test_digit_run_constant_is_bounded() -> None:
    assert 0 < MAX_DIGIT_RUN <= 64


def test_numeric_token_limits_are_bounded() -> None:
    assert MAX_NUMERIC_TOKENS_PER_FIELD > 0
    assert MAX_NUMERIC_TOKENS_PER_MESSAGE >= MAX_NUMERIC_TOKENS_PER_FIELD


def test_candidate_and_match_limits_are_bounded() -> None:
    assert MAX_CANDIDATES > 0
    assert MAX_RULE_MATCHES > 0


def test_repetition_run_limit_is_bounded() -> None:
    assert REPETITION_RUN_LIMIT > 0


# ---------------------------------------------------------------------------
# Pathological repetition
# ---------------------------------------------------------------------------


def test_repetition_does_not_crash_parser() -> None:
    """A 5000-character run of the same letter must not crash the engine."""
    from datetime import datetime

    from packages.parser import parse
    from packages.parser.enums import MessageEvent
    from packages.parser.types import MessageMetadata
    from packages.signal_core.enums import SourceType

    rt = make_runtime("provider_001")
    raw = make_raw("A" * 5000)
    md = MessageMetadata(
        provider_name="provider_001",
        source_type=SourceType.TELEGRAM,
        timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        message_event=MessageEvent.CREATE,
    )
    r = parse(raw, md, rt)
    # Either MALFORMED or NO_SIGNAL; both deterministic.
    assert r.outcome in {ParseResultState.MALFORMED, ParseResultState.NO_SIGNAL}


def test_repetition_truncation_recorded_in_decisions() -> None:
    rt = make_runtime("provider_001")
    norm = normalize("A" * 5000, rt)
    assert "repetition_truncation" in norm.normalization_decisions


# ---------------------------------------------------------------------------
# Unicode edge cases
# ---------------------------------------------------------------------------


def test_emoji_in_message_survives_normalization() -> None:
    rt = make_runtime("provider_001")
    norm = normalize("\U0001f7e2 BUY EURUSD 1.1000 SL 1.0950 TP 1.1100", rt)
    assert "\U0001f7e2" in norm.normalized_text


def test_combining_mark_kept_after_nfkc() -> None:
    rt = make_runtime("provider_001")
    norm = normalize("e\u0301", rt)
    assert "e\u0301" in norm.normalized_text or "é" in norm.normalized_text


# ---------------------------------------------------------------------------
# Determinism / purity (§4.4)
# ---------------------------------------------------------------------------


def test_parser_does_not_call_time_or_random() -> None:
    """The parser module does not import time, random, os.environ, etc."""
    import packages.parser.pipeline as p

    with open(p.__file__) as f:
        src = f.read()
    forbidden = ["time.time", "datetime.now", "uuid.uuid4", "os.environ"]
    for term in forbidden:
        assert term not in src, f"{term!r} found in parser pipeline"


def test_parser_does_not_import_provider_sdk() -> None:
    """The parser package does not import Telegram/Discord/broker SDKs."""
    import sys

    for mod_name in [
        "telegram",
        "telethon",
        "pyrogram",
        "discord",
        "mt4",
        "mt5",
        "ctrader",
        "dxtrade",
        "tradelocker",
    ]:
        assert mod_name not in sys.modules, f"{mod_name!r} unexpectedly imported"


# ---------------------------------------------------------------------------
# Mixed-case keywords never crash (regression — Wave 2 probe finding)
# ---------------------------------------------------------------------------


def test_lowercase_direction_keyword_does_not_crash() -> None:
    """'buy' is classified KEYWORD (case-insensitive, §5.4); the enum lookup
    must canonicalize instead of raising KeyError (design §15: malformed
    input yields outcomes/violations, never exceptions)."""
    from packages.parser import parse
    from packages.signal_core.enums import TradeDirection

    rt = make_runtime("provider_001")
    r = parse(
        make_raw("buy EURUSD 1.1000 SL 1.0950 TP 1.1100"),
        make_metadata("provider_001"),
        rt,
    )
    assert r.outcome is ParseResultState.PARSED
    directions = [f for f in r.ir.fragments if f.slot.name == "DIRECTION"]
    assert directions and directions[0].value is TradeDirection.BUY


def test_mixed_case_direction_keyword_does_not_crash() -> None:
    from packages.parser import parse
    from packages.signal_core.enums import TradeDirection

    rt = make_runtime("provider_001")
    r = parse(
        make_raw("Buy EURUSD 1.1000 SL 1.0950"),
        make_metadata("provider_001"),
        rt,
    )
    assert r.outcome is ParseResultState.PARSED
    directions = [f for f in r.ir.fragments if f.slot.name == "DIRECTION"]
    assert directions and directions[0].value is TradeDirection.BUY


def test_lowercase_canonical_direction_does_not_crash() -> None:
    """provider_003 LONG/SHORT with canonical mapping, lowercase token."""
    from packages.parser import parse
    from packages.signal_core.enums import TradeDirection

    rt = make_runtime("provider_003")
    r = parse(
        make_raw("long BTC 60000 SL 58000 TP 65000"),
        make_metadata("provider_003"),
        rt,
    )
    assert r.outcome is ParseResultState.PARSED
    directions = [f for f in r.ir.fragments if f.slot.name == "DIRECTION"]
    assert directions and directions[0].value is TradeDirection.BUY


def test_lowercase_entry_trigger_does_not_crash() -> None:
    from packages.parser import parse
    from packages.signal_core.enums import EntryTrigger

    rt = make_runtime("provider_006")
    r = parse(
        make_raw("pending buy limit EURUSD 1.1000 SL 1.0950 TP 1.1100"),
        make_metadata("provider_006"),
        rt,
    )
    assert r.outcome is ParseResultState.PARSED
    triggers = [f for f in r.ir.fragments if f.slot.name == "ENTRY_TRIGGER"]
    assert triggers and triggers[0].value is EntryTrigger.LIMIT
