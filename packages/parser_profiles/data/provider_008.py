"""Provider 008 — colon key-value field tables (INFERENCE).

Structural family: fields as ``Label: value`` pairs joined by ``|``
separators (single line or one pair per line). No §21 example uses this
exact syntax; it is a synthetic member of the line-structured axis.

No new semantics: the colon/pipe are DECLARED field separators
(``field_separators``), which makes them glue (§7.4) so value zones like
``SL: 1.0950`` bind like ``SL 1.0950``. SL/TP inherit the common rules via
renamed overrides that additionally declare direction keywords, so a
signal-plus-action message keeps its signal fragments (§20.16-adjacent
action-context tolerance).
"""

from __future__ import annotations

from .common import COMMON_RULE_SET

PROVIDER_008_RULE_SET: dict[str, object] = {
    "name": "provider_008",
    "parent": "common",
    "overrides": [
        ["p008.sl.colon", "common.sl.number"],
        ["p008.tp.colon", "common.tp.number"],
    ],
    "exclusions": [],
    "rules": [
        {
            "id": "p008.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p008.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p008.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p008.entry.between",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {
                    "keywords": ["BUY", "SELL"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "BETWEEN_ANCHORS", "anchors": ["ENTRY", "SL"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "p008.sl.colon",
            "category": "SL",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["SL"]},
            "constraints": ["REQUIRES"],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p008.tp.colon",
            "category": "TP",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["TP"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_008: dict[str, object] = {
    "provider_name": "provider_008",
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
    "rule_set": PROVIDER_008_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
        ["GBPUSD", "GBPUSD"],
    ],
    "tokenizer_pattern": "",
    "field_separators": [":", "|"],
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
