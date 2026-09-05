"""Provider 015 — labeled scalp cards with past-tense entry prose (REAL corpus).

Evidence: docs/corpus/real-messages.md M7, M8 (lines 71-117; the family
self-identifies via the `FXG` line prefix and its site URL in the same
messages). Structural family: `Pair:`/`Direction:` labeled header,
past-tense entry prose (`FXG BOUGHT EURUSD at 1.16122`), ordinal TP1/2/3,
and a dense false-positive tail (accuracy %, position-size %, R-multiple
and pip annotations, lot-size line).

Engine mapping (all data-only):
- direction: Long/Short canonical + BOUGHT/SOLD canonical (same-value
  duplicates dedupe; a message carrying both stays BUY).
- entry: number directly after `at`, gated on BOUGHT/SOLD presence;
  common AT_PRICE condition excluded (here `at` IS the entry).
- SL/TP: REGEX rules — the bracket annotations (`[1 Pips]`, `[1R]`)
  lose their brackets in normalization, so zone rules would absorb the
  annotation numbers as phantom conflicts; regex sites match exactly.
- noise (`±78%`, `2%`, `100 Lots`, `21.28 Lots`, `$1K`) is never bound:
  no rule zone reaches it and whole-message numeric rules bind only
  symbol-adjacent numbers.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET, NUMBER_PATTERN

PROVIDER_015_RULE_SET: dict[str, object] = {
    "name": "provider_015",
    "parent": "common",
    "overrides": [],
    "exclusions": [
        "common.sl.number",
        "common.tp.number",
        "common.condition.at_price",
    ],
    "rules": [
        {
            "id": "p015.direction.long",
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
            "id": "p015.direction.short",
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
            "id": "p015.direction.bought",
            "category": "DIRECTION",
            "matcher": {
                "kind": "LITERAL",
                "params": {"value": "BOUGHT", "canonical": "BUY"},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p015.direction.sold",
            "category": "DIRECTION",
            "matcher": {
                "kind": "LITERAL",
                "params": {"value": "SOLD", "canonical": "SELL"},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p015.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p015.entry.at",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BOUGHT", "SOLD"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["AT"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p015.sl",
            "category": "SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"\bSL\s*:?\s*({NUMBER_PATTERN})",
                    "ignore_case": True,
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
            "id": "p015.tp.ordinal",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"TP\d\s+({NUMBER_PATTERN})",
                    "ignore_case": True,
                    "group": 1,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_015: dict[str, object] = {
    "provider_name": "provider_015",
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
    "rule_set": PROVIDER_015_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
    ],
    "tokenizer_pattern": "",
    "field_separators": [":"],
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
