"""Provider 009 — prose sentences with synonym keywords (INFERENCE).

Structural family: sentence-style messages using direction words
Long/Short (canonicalized to BUY/SELL by explicit ``canonical`` params,
§21.3 pattern) and the synonyms Stop/Target for SL/TP. Keyword
classification is case-insensitive (§5.4), so "We go long EURUSD ...
stop ... target ..." parses like the canonical form.

No new semantics:
- "Stop" must NOT create a pending STOP trigger → common.trigger.stop is
  EXCLUDED for this family (it never sends pending orders).
- prose "at <price>" is an entry preposition, not a conditioned action →
  common.condition.at_price is EXCLUDED; the "at" word breaks the §5.6
  core adjacency so the entry stays UNRESOLVED (PARTIAL) rather than
  being guessed.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET

PROVIDER_009_RULE_SET: dict[str, object] = {
    "name": "provider_009",
    "parent": "common",
    "overrides": [],
    "exclusions": [
        "common.sl.number",
        "common.tp.number",
        "common.trigger.stop",
        "common.condition.at_price",
    ],
    "rules": [
        {
            "id": "p009.direction.long",
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
            "id": "p009.direction.short",
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
            "id": "p009.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p009.entry",
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
        {
            "id": "p009.sl.number",
            "category": "SL",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["LONG", "SHORT"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["SL"]},
            "constraints": ["REQUIRES"],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p009.sl.stopword",
            "category": "SL",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["LONG", "SHORT"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["STOP"]},
            "constraints": ["REQUIRES"],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p009.tp.number",
            "category": "TP",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["LONG", "SHORT"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["TP"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
        {
            "id": "p009.tp.targetword",
            "category": "TP",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["LONG", "SHORT"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["TARGET"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_009: dict[str, object] = {
    "provider_name": "provider_009",
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
    "rule_set": PROVIDER_009_RULE_SET,
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
