"""Provider 002 — multiline, em-dash field separators (design §21.2).

Structural family: line-based layout with em-dash separators between the
field keyword and its value ("SL — 1.0950"). The whitespace-collapse step
of the fixed §5.5.1 pipeline yields a single-line normalized view in which
the em-dash survives as the canonical field separator, so provider rules
are REGEX matchers over that view. The em-dash SL/TP rules MASK the
common keyword rules via renamed overrides (§12.5.7) — exercising the
override mechanism end to end.
"""

from __future__ import annotations

from .common import NUMBER_PATTERN

PROVIDER_002_RULE_SET: dict[str, object] = {
    "name": "provider_002",
    "parent": "common",
    "overrides": [
        ["p002.sl.emdash", "common.sl.number"],
        ["p002.tp.emdash", "common.tp.number"],
    ],
    "exclusions": [],
    "rules": [
        {
            "id": "p002.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p002.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p002.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p002.entry.after_keyword",
            "category": "ENTRY",
            "matcher": {"kind": "NUMBER"},
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["ENTRY"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "p002.sl.emdash",
            "category": "SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"SL\s*—\s*({NUMBER_PATTERN})",
                    "group": 1,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p002.tp.emdash",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"TP\s*—\s*({NUMBER_PATTERN})",
                    "group": 1,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_002: dict[str, object] = {
    "provider_name": "provider_002",
    "version": "2B",
    "capabilities": {
        "close_full": True,
        "close_half": True,
        "profit_close": False,
        "move_sl_breakeven": True,
        "remove_sl": True,
        "cancel_pending": True,
        "trigger_pending": True,
        "move_sl_number": True,
        "move_sl_conditional": False,
        "move_tp_conditional": True,
        "move_entry_conditional": True,
        "edit_handling": True,
        "delete_handling": True,
        "reply_required": False,
        "negative_keywords": True,
        "last_signal_execution": True,
        "trailing": False,
        "multi_signal": False,
        "multi_message": True,
    },
    "rule_set": PROVIDER_002_RULE_SET,
    "symbol_aliases": [["EURUSD", "EURUSD"], ["GBPJPY", "GBPJPY"]],
    "tokenizer_pattern": "",
    "field_separators": ["—"],
    "multi_value_separators": ["/"],
    "decimal_format": "dot",
    "range_patterns": ["-"],
    "multiline_mode": True,
    "reply_requirement": "NONE",
    "edit_behavior": "REPARSE_DELTA",
    "delete_behavior": "CANCEL_TARGET",
    "follow_up_behavior": "TARGET_LAST_SIGNAL",
    "max_message_length": 8000,
    "max_numeric_value": "1e12",
}
