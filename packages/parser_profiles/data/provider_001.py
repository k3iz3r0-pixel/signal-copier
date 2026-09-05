"""Provider 001 — inline, comma-separated fields (design §21.1).

Structural family: single-line, comma-separated field list, explicit
entry/SL/TP keywords, decimal-point numbers. Entry levels are the numbers
BEFORE the SL anchor; a price-range form ("2350-2360") outranks a single
number by the §7.3 longer-match rule.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET

PROVIDER_001_RULE_SET: dict[str, object] = {
    "name": "provider_001",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p001.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p001.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p001.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p001.entry.range",
            "category": "ENTRY",
            "matcher": {
                "kind": "PRICE_RANGE",
                "params": {
                    "keywords": ["BUY", "SELL"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 5,
            "occurrence": "FIRST",
        },
        {
            "id": "p001.entry.levels",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {
                    "keywords": ["BUY", "SELL"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "BEFORE_TOKEN", "anchors": ["SL"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "ALL",
        },
        {
            "id": "p001.entry.first",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {
                    "keywords": ["BUY", "SELL"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 40,
            "occurrence": "FIRST",
        },
    ],
}

PROVIDER_001: dict[str, object] = {
    "provider_name": "provider_001",
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
    "rule_set": PROVIDER_001_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
        ["GBPUSD", "GBPUSD"],
        ["XAUUSD", "XAUUSD"],
        ["NAS100", "NAS100"],
    ],
    "tokenizer_pattern": "",
    "field_separators": [],
    "multi_value_separators": ["/"],
    "decimal_format": "dot",
    "range_patterns": ["-"],
    "multiline_mode": False,
    "reply_requirement": "NONE",
    "edit_behavior": "REPARSE_DELTA",
    "delete_behavior": "CANCEL_TARGET",
    "follow_up_behavior": "TARGET_LAST_SIGNAL",
    "max_message_length": 8000,
    "max_numeric_value": "1e12",
}

_ALL_RULE_SETS = {"common": COMMON_RULE_SET}
