"""Provider 013 — bracket-annotated ticket blocks (REAL corpus family).

Evidence: docs/corpus/real-messages.md M1-M4 (lines 1-48); M3 carries the
family's public channel link, M1/M2/M4 share the same ticket/decoration
grammar. Structural family: ticket-header + `Field: value` block with
bracket annotations, plus a `{ Moved SL }` action variant.

Engine mapping (all data-only; no pipeline changes):
- Header `NEW` keyword gates direction/entry/instrument (REQUIRES on REGEX
  rules — M1 closed-event and M3 weekly report carry no NEW and must stay
  NO_SIGNAL).
- Field rules are REGEX-captured (Entry:/SL:/TP:) because `normalize`
  strips markdown brackets — zone rules would absorb the pips annotations
  (`[39.9 Pips]`) and create phantom conflicts; regex sites match exactly.
- `Old SL:` is FORBIDS-gated so M4's action block never yields SL
  candidates (old/new SL values would conflict).
- `New SL: <num>` is the family's move-SL phrasing → ACTION_MOVE_SL with
  the level in the evidence snippet (§8 semantics, same as §20.13).
- `Stop moved to Breakeven` is the prose duplicate of the same numeric
  move; emitting BREAKEVEN too would create an ACTION conflict, so the
  numeric new-SL is the operative instruction (documented).
"""

from __future__ import annotations

from .common import COMMON_RULE_SET, NUMBER_PATTERN

PROVIDER_013_RULE_SET: dict[str, object] = {
    "name": "provider_013",
    "parent": "common",
    "overrides": [],
    "exclusions": ["common.sl.number", "common.tp.number", "common.trigger.stop"],
    "rules": [
        {
            "id": "p013.direction",
            "category": "DIRECTION",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"\b(BUY|SELL)\b",
                    "ignore_case": True,
                    "group": 1,
                    "keywords": ["NEW"],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REQUIRES"],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p013.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p013.entry",
            "category": "ENTRY",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"Entry\s*:\s*({NUMBER_PATTERN})",
                    "ignore_case": True,
                    "group": 1,
                    "keywords": ["NEW"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p013.sl",
            "category": "SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"SL\s*:\s*({NUMBER_PATTERN})",
                    "ignore_case": True,
                    "group": 1,
                    "keywords": ["OLD"],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["FORBIDS"],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p013.tp",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"TP\s*:\s*({NUMBER_PATTERN})",
                    "ignore_case": True,
                    "group": 1,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "TP",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p013.action.new_sl",
            "category": "ACTION_MOVE_SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"NEW\s+SL\s*:\s*({NUMBER_PATTERN})",
                    "ignore_case": True,
                    "group": 1,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 15,
            "occurrence": "FIRST",
        },
    ],
}

PROVIDER_013: dict[str, object] = {
    "provider_name": "provider_013",
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
    "rule_set": PROVIDER_013_RULE_SET,
    "symbol_aliases": [
        ["XAUUSD", "XAUUSD"],
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
