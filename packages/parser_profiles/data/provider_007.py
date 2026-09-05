"""Provider 007 — ordinal take-profit labels (TP1/TP2/TP3). INFERENCE.

Structural family: an inline signal whose multiple take-profits carry
ordinal labels instead of the slash multi-value form —
"BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950". There is no §21
example with this exact syntax; it is constructed as a synthetic member
of the "multiple TP forms" capability axis (design §21 examples are
themselves marked INFERENCE). No undocumented provider SEMANTICS are
introduced: ordinal labels denote take-profit levels exactly like the
documented slash form.

Engine mapping (verified without pipeline changes):

- the ordinal digits in "TP1" tokenize as separate NUMBER tokens, so the
  inherited common TP rule (AFTER_TOKEN "TP") would mis-bind them; the
  profile therefore EXCLUDES ``common.tp.number`` and provides its own
  REGEX TP rule ``TP\\d\\s+(number)`` whose group 1 captures only the
  level (occurrence=ALL, REPEATABLE);
- entry is the number between the direction keyword and the first TP
  label, bound by BETWEEN_ANCHORS NUMBER rules (one per direction), which
  the ordinal digits can never pollute (they live after the TP anchor).

The unmatched "TP"-form (plain "TP 1.1100") is deliberately NOT bound by
this profile: this provider's documented form is ordinal-labeled only.
"""

from __future__ import annotations

from .common import NUMBER_PATTERN

PROVIDER_007_RULE_SET: dict[str, object] = {
    "name": "provider_007",
    "parent": "common",
    "overrides": [],
    "exclusions": ["common.tp.number"],
    "rules": [
        {
            "id": "p007.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p007.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p007.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p007.entry.from_buy",
            "category": "ENTRY",
            "matcher": {"kind": "NUMBER"},
            "scope": {"kind": "BETWEEN_ANCHORS", "anchors": ["BUY", "TP"]},
            "constraints": [],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "p007.entry.from_sell",
            "category": "ENTRY",
            "matcher": {"kind": "NUMBER"},
            "scope": {"kind": "BETWEEN_ANCHORS", "anchors": ["SELL", "TP"]},
            "constraints": [],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "p007.tp.labeled",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": rf"TP\d\s+({NUMBER_PATTERN})", "group": 1},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
    ],
}

PROVIDER_007: dict[str, object] = {
    "provider_name": "provider_007",
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
    "rule_set": PROVIDER_007_RULE_SET,
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
