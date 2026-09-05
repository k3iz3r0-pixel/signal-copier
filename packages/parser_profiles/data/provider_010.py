"""Provider 010 — unusual field ordering (INFERENCE).

Structural family: SL/TP fields BEFORE the entry, and the instrument
AFTER all price fields:

``BUY SL 1.0950 TP 1.1100 EURUSD 1.1000``

No §21 example uses this exact ordering; it is a synthetic member of the
unusual-field-ordering axis (§21 examples are themselves marked
INFERENCE). No new semantics: the engine's bounded value zones and §5.6
core adjacency are order-independent by construction — this profile is
pure data exercising that property.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET

PROVIDER_010_RULE_SET: dict[str, object] = {
    "name": "provider_010",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p010.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p010.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p010.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p010.entry",
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
            "priority": 20,
            "occurrence": "FIRST",
        },
    ],
}

PROVIDER_010: dict[str, object] = {
    "provider_name": "provider_010",
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
    "rule_set": PROVIDER_010_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
        ["GBPUSD", "GBPUSD"],
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
