"""Regex safety validator regression tests (Phase 2B.1 remediation).

The audit verified that the previous validator accepted dangerous shapes
equivalent to ``(a|a)*b`` — an ambiguous alternation under an unbounded
quantifier — which exhibits exponential backtracking in ``re`` (measured:
~2.7 s at 25 input characters for ``(a|a)*b``).

The remediated validator is a STRUCTURAL safety analysis: it parses the
pattern and rejects every unbounded quantifier whose operand

- contains a nested unbounded quantifier,
- contains a variable-width quantifier (ambiguous iteration boundaries),
- can match empty (infinite loop), or
- contains an alternation whose branch FIRST sets overlap, are statically
  unknown, or can be empty.

No runtime timeout is involved; the analysis is static and deterministic.
All currently accepted provider patterns must keep compiling (preserved
below); safe-but-exotic shapes such as fixed-width bodies under an
unbounded quantifier (``(?:a{2})*``) remain accepted.
"""

from __future__ import annotations

import pytest

from packages.parser.safety import (
    MAX_PATTERN_LENGTH,
    UnsafePatternError,
    check_pattern_safe,
    compile_safe,
)
from packages.parser_profiles import get_profile

DANGEROUS_PATTERNS = [
    r"(a|a)*b",  # the verified false positive
    r"(?:ab|a)*c",  # branch prefix of another branch
    r"(?:ab|ac)*d",  # shared first character
    r"(a+)+",  # nested unbounded
    r"(a*)*b",
    r"(a+)*b",
    r"(?:a*b)*",  # unbounded inside unbounded
    r"(?:a+b)*",
    r"(?:ab?)*c",  # variable-width under unbounded (ambiguous splits)
    r"(a{2,3})*b",  # variable-width bounded under unbounded
    r"(a{1,2})*b",
    r"(?:\w|a)*",  # unanalyzable first-set (class) vs literal
    r"(?:[^x]|a)*",  # negated class -> unknown first set
    r"(?:\d+-\d+)*x",  # class-anchored ambiguous branches
    r"(?:a|)*b",  # empty branch under unbounded
    r"()*",  # empty body
    r"x*(?:a|a)*y",
    r"(?=(a+)+)b",  # dangerous shape hidden inside a lookahead
    r"(?:(a|a)){2}b",  # fixed-width wrapper around ambiguous alternation
    r"(?:ab){2}*",  # multiple quantifiers on one operand (invalid re syntax)
    r"(a)\1",  # backreference
    r"(?<=a)b",  # lookbehind
]

SAFE_PATTERNS = [
    # currently accepted provider/profile patterns (must keep compiling)
    r"CLOSE\s+HALF",
    r"CLOSE\s+(\d{1,3})\s*%",
    r"MOVE\s+SL\s+TO\s+(?:BE|BREAKEVEN|ENTRY)",
    r"REMOVE\s+SL",
    r"(?:CHANGE\s+)?SL\s+(\d{1,13}(?:\.\d{1,12})?)",
    r"CHANGE\s+TP(?:\s+TO)?\s+(\d{1,13}(?:\.\d{1,12})?)",
    r"CHANGE\s+ENTRY\s+TO\s+(\d{1,13}(?:\.\d{1,12})?)",
    r"CANCEL\s+PENDING",
    r"TRIGGER\s+PENDING",
    r"\bAT\s+(\d{1,13}(?:\.\d{1,12})?)",
    r"SL\s*—\s*(\d{1,13}(?:\.\d{1,12})?)",
    r"TP\s*—\s*(\d{1,13}(?:\.\d{1,12})?)",
    r"(?i)CLOSE\s+HALF",
    r"(?i)REMOVE\s+SL",
    r"(?i)CANCEL\s+PENDING",
    r"(?i)TRIGGER\s+PENDING",
    r"(?i)MOVE\s+SL\s+TO\s+(?:BE|BREAKEVEN|ENTRY)",
    r"\d{1,13}(?:\.\d{1,12})?",
    r"\d{1,13}(?:\.\d{1,12})?|[A-Za-z]{1,16}|\s|[^\sA-Za-z0-9]",
    # generically safe shapes
    r"a*",
    r"a*b*c*",
    r"\s+",
    r"[A-Za-z]{1,16}",
    r"a{2,}",
    r"a{,5}b",
    r"a*?",
    r"a*+",
    r"(?:a|b)*c",  # disjoint literal branches under repetition
    r"(?:BUY|SELL)+",
    r"(?:ab|cd)*e",  # disjoint multi-char branches
    r"(?:aa|bb)*x",  # disjoint first sets
    r"(?:\w\w)*x",  # fixed two-class body, no alternation
    r"(?:a{2})*b",  # FIXED-width body under unbounded quantifier
    r"(\w\s)*z",
    r"(?:BE|BREAKEVEN|ENTRY)",  # alternation WITHOUT quantifier
]


@pytest.mark.parametrize("pattern", DANGEROUS_PATTERNS)
def test_dangerous_patterns_are_rejected(pattern: str) -> None:
    with pytest.raises(UnsafePatternError):
        check_pattern_safe(pattern)


@pytest.mark.parametrize("pattern", SAFE_PATTERNS)
def test_safe_patterns_are_accepted(pattern: str) -> None:
    check_pattern_safe(pattern)
    compile_safe(pattern)


def test_overlong_pattern_rejected() -> None:
    with pytest.raises(UnsafePatternError):
        check_pattern_safe("a" * (MAX_PATTERN_LENGTH + 1))


def test_validator_does_not_rely_on_runtime_timeout() -> None:
    """The guarantee is static: validation of a dangerous pattern must be
    effectively instantaneous (no execution, no timing)."""
    import time

    start = time.perf_counter()
    for _ in range(100):
        with pytest.raises(UnsafePatternError):
            check_pattern_safe(r"(a|a)*b")
    assert time.perf_counter() - start < 1.0


def test_all_loaded_profiles_use_only_safe_patterns() -> None:
    """Every compiled artifact of every provider profile passes the
    structural validator (preserved safe provider patterns)."""
    from packages.parser.safety import check_pattern_safe as check

    for provider in ("provider_001", "provider_002", "provider_003"):
        rt = get_profile(provider)
        check(rt.profile.tokenizer_pattern or rt.tokenizer.pattern)
        for pattern in rt.rule_patterns.values():
            check(pattern.pattern)
