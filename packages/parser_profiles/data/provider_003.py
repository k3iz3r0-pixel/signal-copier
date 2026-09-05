"""Provider 003 — bitcoin-style, no decimals, LONG/SHORT keywords (§21.3).

Structural family: crypto-style integer prices, direction expressed as
LONG/SHORT (canonicalized to BUY/SELL by the rule's explicit ``canonical``
param with the raw text preserved in evidence), and crypto symbols via
the alias table.
"""

from __future__ import annotations

PROVIDER_003_RULE_SET: dict[str, object] = {
    "name": "provider_003",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p003.direction.long",
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
            "id": "p003.direction.short",
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
            "id": "p003.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p003.entry.range",
            "category": "ENTRY",
            "matcher": {
                "kind": "PRICE_RANGE",
                "params": {
                    "keywords": ["LONG", "SHORT"],
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
            "id": "p003.entry.first",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {
                    "keywords": ["LONG", "SHORT"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "FIRST",
        },
    ],
}

PROVIDER_003: dict[str, object] = {
    "provider_name": "provider_003",
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
    "rule_set": PROVIDER_003_RULE_SET,
    "symbol_aliases": [["BTC", "BTC"], ["ETH", "ETH"]],
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
