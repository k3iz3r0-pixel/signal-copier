"""Provider 014 — core real-world one-liners and labeled levels (REAL corpus).

Evidence: docs/corpus/real-messages.md M5, M6, M9-M13, M17, M21, M22,
M24, M25, M31 (the corpus's dominant family: inline core signals, both
one-liners and labeled blocks). This family validates the COMMON grammar
itself against real data and adds the corpus-required variants:

- entry after direction (one-liners), after `Entry` label, after `limit`,
  after `now`, and symbol-adjacent (whole-message rule binds only
  symbol-adjacent numbers — prose numbers can never be hijacked);
- slash entry ranges (PRICE_RANGE over range_patterns ["-","/"], gated on
  a co-occurring SL token so prose ranges — M9's `300/250 region` — never
  become entries);
- repeated unlabeled TPs (regex `TP` + optional colon, ALL) and labeled
  `Take profit:` TPs (AFTER_TOKEN PROFIT, TAKE-gated);
- `Stop loss:` SL (AFTER_TOKEN LOSS, STOP-gated) — the `Stop` token must
  NOT become a STOP-order trigger (common.trigger.stop excluded);
- `now` → MARKET canonical trigger, FORBIDS-gated on LIMIT;
- `Sell Gold`-style no-entry messages stay PARTIAL (entry_pending);
  commentary (M6) stays NO_SIGNAL.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET, NUMBER_PATTERN

PROVIDER_014_RULE_SET: dict[str, object] = {
    "name": "provider_014",
    "parent": "common",
    "overrides": [],
    "exclusions": [
        "common.trigger.stop",
        "common.sl.number",
        "common.tp.number",
    ],
    "rules": [
        {
            "id": "p014.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.entry.range",
            "category": "ENTRY",
            "matcher": {
                "kind": "PRICE_RANGE",
                "params": {"keywords": ["SL"], "requires_symbol": True},
            },
            "scope": {"kind": "BEFORE_TOKEN", "anchors": ["SL"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 5,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.entry.after_buy",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["BUY"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "ALL",
        },
        {
            "id": "p014.entry.after_sell",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["SELL"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "ALL",
        },
        {
            "id": "p014.entry.after_now",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["NOW"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.entry.label",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["ENTRY"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.entry.after_limit",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["LIMIT"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.entry.first",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 40,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.sl.regex",
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
            "id": "p014.tp.regex",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"\bTP\s*:?\s*({NUMBER_PATTERN})",
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
            "id": "p014.tp.take_profit",
            "category": "TP",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["TAKE"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["PROFIT"]},
            "constraints": ["REQUIRES", "REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
        {
            "id": "p014.sl.stop_loss",
            "category": "SL",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["STOP"]},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["LOSS"]},
            "constraints": ["REQUIRES"],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p014.trigger.now",
            "category": "ENTRY_TRIGGER",
            "matcher": {
                "kind": "LITERAL",
                "params": {
                    "value": "NOW",
                    "canonical": "MARKET",
                    "keywords": ["LIMIT"],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["FORBIDS"],
            "target": "ENTRY_TRIGGER",
            "priority": 10,
            "occurrence": "FIRST",
        },
    ],
}

PROVIDER_014: dict[str, object] = {
    "provider_name": "provider_014",
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
    "rule_set": PROVIDER_014_RULE_SET,
    "symbol_aliases": [
        ["EURUSD", "EURUSD"],
        ["GBPJPY", "GBPJPY"],
        ["XAUUSD", "XAUUSD"],
        ["GOLD", "XAUUSD"],
        ["USDJPY", "USDJPY"],
        ["US30", "US30"],
        ["AUDJPY", "AUDJPY"],
    ],
    "tokenizer_pattern": "",
    "field_separators": [":"],
    "multi_value_separators": ["/"],
    "decimal_format": "dot",
    "range_patterns": ["-", "/"],
    "multiline_mode": False,
    "reply_requirement": "NONE",
    "edit_behavior": "REPARSE_DELTA",
    "delete_behavior": "CANCEL_TARGET",
    "follow_up_behavior": "TARGET_LAST_SIGNAL",
    "max_message_length": 8000,
    "max_numeric_value": "1e12",
}

_ALL_RULE_SETS = {"common": COMMON_RULE_SET}
