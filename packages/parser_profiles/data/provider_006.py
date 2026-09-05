"""Provider 006 — pending-order style (design §21.8).

Structural family: an explicit "PENDING" prefix before a direction +
trigger keyword pair ("PENDING BUY LIMIT EURUSD 1.1000 ..."), inline
field ordering, and a pending-order lifecycle driven by the common
follow-up actions (CANCEL PENDING / TRIGGER PENDING). The "PENDING"
word itself is unclaimed decoration: the order-pending nature of the
signal is carried by the ENTRY_TRIGGER fragment (LIMIT/STOP/MARKET via
the common trigger rules), which is the canonical representation the
design provides.

Entry binding follows the p001 claims model: the zone rule BEFORE the
SL anchor owns the entry value; a whole-message first-number rule with
direction-keyword + symbol gating serves as the fallback for messages
without an SL (its keyword-less-number protections still apply, so a
number separated from the symbol by "@" or prose is left unbound).
"""

from __future__ import annotations

PROVIDER_006_RULE_SET: dict[str, object] = {
    "name": "provider_006",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p006.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p006.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p006.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p006.entry.zone",
            "category": "ENTRY",
            "matcher": {"kind": "NUMBER"},
            "scope": {"kind": "BEFORE_TOKEN", "anchors": ["SL"]},
            "constraints": ["REPEATABLE"],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "ALL",
        },
        {
            "id": "p006.entry.first",
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

PROVIDER_006: dict[str, object] = {
    "provider_name": "provider_006",
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
    "rule_set": PROVIDER_006_RULE_SET,
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
