"""Regression tests: LINE scope (design §7.1 — "match within one line").

Whitespace collapse (§5.5 step 4) erases line structure from the
normalized text, so the LINE scope is implemented over the SourceMap: a
LINE-scoped rule matches only inside normalized windows whose raw
projection stays within one raw line of the original message. These tests
pin the raw-line semantics (LF, CRLF, collapsed multi-char runs) and the
claims interplay with whole-message rules.
"""

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.parser.profiles import load_profile
from packages.parser.types import ProviderCapabilities
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw

_ALL_OFF = {flag: False for flag in ProviderCapabilities.__dataclass_fields__}

_BASE_RULES = [
    {
        "id": "line.direction.buy",
        "category": "DIRECTION",
        "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
        "scope": {"kind": "WHOLE_MESSAGE"},
        "constraints": [],
        "target": "DIRECTION",
        "priority": 10,
        "occurrence": "FIRST",
    },
    {
        "id": "line.direction.sell",
        "category": "DIRECTION",
        "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
        "scope": {"kind": "WHOLE_MESSAGE"},
        "constraints": [],
        "target": "DIRECTION",
        "priority": 10,
        "occurrence": "FIRST",
    },
    {
        "id": "line.instrument",
        "category": "INSTRUMENT",
        "matcher": {"kind": "SYMBOL"},
        "scope": {"kind": "WHOLE_MESSAGE"},
        "constraints": [],
        "target": "INSTRUMENT",
        "priority": 10,
        "occurrence": "FIRST",
    },
    {
        "id": "line.entry.number",
        "category": "ENTRY",
        "matcher": {"kind": "NUMBER"},
        "scope": {"kind": "WHOLE_MESSAGE"},
        "constraints": [],
        "target": "ENTRY",
        "priority": 20,
        "occurrence": "FIRST",
    },
]


def _profile(rules, capabilities=None):
    return {
        "provider_name": "lineprov",
        "version": "2B",
        "capabilities": capabilities or _ALL_OFF,
        "field_separators": ["—"],
        "multi_value_separators": ["/"],
        "decimal_format": "dot",
        "range_patterns": ["-"],
        "symbol_aliases": [["EURUSD", "EURUSD"]],
        "rule_set": {"name": "lineprov", "rules": rules},
    }


def _runtime(rules, capabilities=None):
    return load_profile(_profile(list(_BASE_RULES) + list(rules), capabilities), {})


def _parse(text, runtime):
    return parse(make_raw(text), make_metadata("lineprov"), runtime)


_CROSS_LINE_RULE = {
    "id": "line.cross",
    "category": "CONDITION",
    "matcher": {
        "kind": "REGEX",
        "params": {"pattern": r"EURUSD\s+SELL", "condition_kind": "KEYWORD_PRESENT"},
    },
    "scope": {"kind": "LINE"},
    "constraints": [],
    "target": "CONDITION",
    "priority": 10,
    "occurrence": "FIRST",
}

_CROSS_LINE_RULE_WHOLE = dict(_CROSS_LINE_RULE, id="line.cross.whole")
_CROSS_LINE_RULE_WHOLE["scope"] = {"kind": "WHOLE_MESSAGE"}


def test_line_scope_rejects_match_crossing_line_boundary() -> None:
    """'EURUSD SELL' only exists after newline collapse; a LINE-scoped rule
    must NOT match it, while the same pattern under WHOLE_MESSAGE does."""
    text = "BUY EURUSD\nSELL GBPUSD"
    line_r = _parse(text, _runtime([_CROSS_LINE_RULE]))
    assert line_r.ir.conditions == ()
    whole_r = _parse(text, _runtime([_CROSS_LINE_RULE_WHOLE]))
    assert len(whole_r.ir.conditions) == 1
    condition = whole_r.ir.conditions[0]
    assert condition.kind.name == "KEYWORD_PRESENT"
    assert condition.params == (("keyword", "EURUSD SELL"),)


def test_line_scope_matches_within_each_line() -> None:
    """One window per raw line: a LINE-scoped ALL-occurrence rule binds the
    value on each line (deterministic order)."""
    level_rule = {
        "id": "line.level",
        "category": "TP",
        "matcher": {
            "kind": "REGEX",
            "params": {
                "pattern": r"LEVEL\s+(\d{1,13}(?:\.\d{1,12})?)",
                "group": 1,
            },
        },
        "scope": {"kind": "LINE"},
        "constraints": [],
        "target": "TP",
        "priority": 10,
        "occurrence": "ALL",
    }
    r = _parse("LEVEL 1.1000\nLEVEL 1.1050", _runtime([level_rule]))
    tp = [f for f in r.ir.fragments if f.slot is CandidateSlot.TP]
    assert tp and tp[0].value == (
        Price(Decimal("1.1000")),
        Price(Decimal("1.1050")),
    )


def test_line_scope_without_newlines_equals_whole_message() -> None:
    r = _parse("BUY EURUSD 1.1000", _runtime([_CROSS_LINE_RULE]))
    assert r.outcome is ParseResultState.PARSED
    assert r.ir.conditions == ()


def test_line_scope_with_crlf_line_endings() -> None:
    """CRLF collapses into one boundary space; the line boundary still
    separates the windows."""
    text = "BUY EURUSD\r\nSELL GBPUSD"
    r = _parse(text, _runtime([_CROSS_LINE_RULE]))
    assert r.ir.conditions == ()


def test_line_boundary_inside_collapsed_whitespace_run() -> None:
    """A single collapsed space whose raw run is '  \\n \\t' is a boundary:
    matches may not span it even though the normalized text shows one
    space."""
    text = "BUY EURUSD  \n \t SELL GBPUSD"
    r = _parse(text, _runtime([_CROSS_LINE_RULE]))
    assert r.ir.conditions == ()


_LEVEL_CLAIM_RULE = {
    "id": "line.level.claim",
    "category": "TP",
    "matcher": {
        "kind": "REGEX",
        "params": {"pattern": r"(\d{1,13}(?:\.\d{1,12})?)", "group": 1},
    },
    "scope": {"kind": "LINE"},
    "constraints": [],
    "target": "TP",
    "priority": 5,
    "occurrence": "ALL",
}


def test_line_scoped_rule_claims_its_lines_numbers() -> None:
    """A LINE-scoped non-ENTRY rule CLAIMS the numbers on its lines: the
    keyword-less whole-message entry rule may not re-bind them (§5.6)."""
    text = "BUY EURUSD 1.1000\nLEVEL 2.0000"
    with_rule = _parse(
        text,
        _runtime([_LEVEL_CLAIM_RULE], {**_ALL_OFF, "multi_message": True}),
    )
    assert with_rule.outcome is ParseResultState.PARTIAL
    resolved_entries = [
        f
        for f in with_rule.ir.fragments
        if f.slot is CandidateSlot.ENTRY and f.value is not None
    ]
    assert resolved_entries == []
    without_rule = _parse(text, _runtime([]))
    entry = [f for f in without_rule.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert entry and entry[0].value == Price(Decimal("1.1000"))
    assert without_rule.outcome is ParseResultState.PARSED


def test_line_scope_is_deterministic() -> None:
    text = "BUY EURUSD 1.1000\nLEVEL 2.0000"
    runtime = _runtime([_LEVEL_CLAIM_RULE])
    first = _parse(text, runtime)
    second = _parse(text, runtime)
    assert first.ir == second.ir
    assert first.outcome is second.outcome
