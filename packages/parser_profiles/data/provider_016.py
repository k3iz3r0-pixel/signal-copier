"""Provider 016 — @-separated signal levels (REAL corpus family).

Evidence: docs/corpus/real-messages.md M23, M26 (lines 282-307; shared
`Sell Gold/XAGUSD @ <price>` grammar, one message per structure).
Structural family: `@` as the level separator — `SL @ 67.0731`,
`TP @ 61.3857`, and `@` between instrument and entry.

Engine mapping (all data-only):
- `@` is declared as a field separator (glue), so `SL @ x` / `TP @ x`
  bind through the value-zone adjacency; entry uses the BEFORE_TOKEN SL
  zone FIRST (all numbers before the SL anchor, annotations excluded by
  ownership of the SL value).
- ordinal `Tp1/Tp2` TPs use the reusable ordinal regex; `TP @` TPs use
  the @-labeled regex. common.tp.number is excluded — a zone rule would
  absorb the ordinal digit of `Tp1` as a phantom TP value.
- XAGUSD alias added (corpus message); GOLD→XAUUSD (corpus-supported:
  `GOLD/XAUUSD` equivalence and `Gold` usage elsewhere in the corpus).
"""

from __future__ import annotations

from .common import COMMON_RULE_SET, NUMBER_PATTERN

PROVIDER_016_RULE_SET: dict[str, object] = {
    "name": "provider_016",
    "parent": "common",
    "overrides": [],
    "exclusions": ["common.tp.number"],
    "rules": [
        {
            "id": "p016.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p016.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p016.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p016.entry.before_sl",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "BEFORE_TOKEN", "anchors": ["SL"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p016.tp.at",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"TP\s*@\s*({NUMBER_PATTERN})",
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
        {
            "id": "p016.tp.ordinal",
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

PROVIDER_016: dict[str, object] = {
    "provider_name": "provider_016",
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
    "rule_set": PROVIDER_016_RULE_SET,
    "symbol_aliases": [
        ["XAGUSD", "XAGUSD"],
        ["GOLD", "XAUUSD"],
        ["XAUUSD", "XAUUSD"],
    ],
    "tokenizer_pattern": "",
    "field_separators": ["@"],
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
