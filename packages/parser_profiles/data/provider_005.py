"""Provider 005 — multi-line numbered entry levels (design §21.7).

Structural family: a "SCALP" header followed by ordinal-prefixed entry
levels on their own lines ("1) 3350"), then SL/TP keyword lines. The
levels are captured by a LINE-scoped REGEX whose group 1 skips the
ordinal prefix, so "1)"-style ordinals can never themselves become
prices. Multiple levels accumulate under occurrence=ALL; the ladder
order (which the design example shows descending) is preserved verbatim
in the IR — the parser never reorders prices.

The design example carries no instrument symbol; the parser leaves
INSTRUMENT unresolved and still reports PARSED (instrument is
downstream-required, not parser-required). A SELL direction rule is
included so short ladders are representable (INFERENCE beyond the
§21.7 example, same family syntax).
"""

from __future__ import annotations

from .common import NUMBER_PATTERN

PROVIDER_005_RULE_SET: dict[str, object] = {
    "name": "provider_005",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p005.direction.long",
            "category": "DIRECTION",
            "matcher": {
                "kind": "LITERAL",
                "params": {"value": "LONG", "canonical": "BUY"},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p005.direction.short",
            "category": "DIRECTION",
            "matcher": {
                "kind": "LITERAL",
                "params": {"value": "SHORT", "canonical": "SELL"},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p005.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p005.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p005.entry.levels",
            "category": "ENTRY",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"\d{{1,2}}\)\s*({NUMBER_PATTERN})",
                    "group": 1,
                },
            },
            "scope": {"kind": "LINE"},
            "constraints": ["REPEATABLE"],
            "target": "ENTRY",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_005: dict[str, object] = {
    "provider_name": "provider_005",
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
    "rule_set": PROVIDER_005_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
        ["XAUUSD", "XAUUSD"],
    ],
    "tokenizer_pattern": "",
    "field_separators": [],
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
