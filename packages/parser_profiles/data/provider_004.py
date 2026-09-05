"""Provider 004 — emoji field markers, line-structured (design §21.4).

Structural family: each field is introduced by a dedicated emoji marker on
its own line (🎯 entry, 🛑 SL, 💰 TP) with a status emoji + hashtag symbol
header line. The emoji characters survive normalization (NFKC-stable,
non-whitespace, non-markdown) and are matched by REGEX rules over LINE
scopes: the 2B.2 line-window machinery keeps each match inside one raw
line, so a marker on line N can never capture a number on line N+1.

Direction/instrument come from the header line ("🟢 BUY #EURUSD"): the
leading emoji is unclaimed decoration, "#" is stripped as markdown syntax
by the fixed normalization step 3, leaving BUY + the symbol for the
LITERAL/SYMBOL rules. Common SL/TP/action rules remain inherited and add
keyword-form acceptance on top of the emoji form.
"""

from __future__ import annotations

from .common import NUMBER_PATTERN

MARKER_ENTRY = "\U0001f3af"  # 🎯
MARKER_SL = "\U0001f6d1"  # 🛑
MARKER_TP = "\U0001f4b0"  # 💰

PROVIDER_004_RULE_SET: dict[str, object] = {
    "name": "provider_004",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p004.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p004.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p004.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p004.entry.marker",
            "category": "ENTRY",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"{MARKER_ENTRY}\s*({NUMBER_PATTERN})",
                    "group": 1,
                },
            },
            "scope": {"kind": "LINE"},
            "constraints": [],
            "target": "ENTRY",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p004.sl.marker",
            "category": "SL",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": rf"{MARKER_SL}\s*({NUMBER_PATTERN})", "group": 1},
            },
            "scope": {"kind": "LINE"},
            "constraints": [],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p004.tp.marker",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": rf"{MARKER_TP}\s*({NUMBER_PATTERN})", "group": 1},
            },
            "scope": {"kind": "LINE"},
            "constraints": ["REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_004: dict[str, object] = {
    "provider_name": "provider_004",
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
    "rule_set": PROVIDER_004_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
        ["GBPUSD", "GBPUSD"],
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
