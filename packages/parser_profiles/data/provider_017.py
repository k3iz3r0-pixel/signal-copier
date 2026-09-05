"""Provider 017 — prose `at` entries, NOW market wording, follow-up moves.

Evidence: docs/corpus/real-messages.md M16, M27, M30 (lines 195-198,
309-327, 344-348; shared prose-entry grammar: `... at <price>`, `SELL
NOW at`, and the `Move SL at` follow-up phrasing).

Engine mapping (all data-only):
- entry: number directly after `at`, gated on BUY/SELL presence;
  common AT_PRICE condition excluded (here `at` IS the entry).
- NOW → MARKET via a REGEX rule with FORBIDS [LIMIT]: "SELL NOW" is
  market execution (M30) while "SELL LIMIT now" uses `now` as a temporal
  adverb (M27) — the LIMIT presence suppresses the market reading.
  REGEX (not LITERAL) is required: LITERAL keyword-token candidates
  bypass constraints and would leave an un-gated MARKET candidate next
  to LIMIT (engine probe showed AMBIGUOUS_TRIGGER).
- `Move SL at <num>` → ACTION_MOVE_SL with the level in the evidence
  snippet (§8/§20.13 semantics). The `TP1 HIT` status line in M16 must
  not bind (the ordinal regex requires a number after the label).
- SL: inherited common zone rule is safe here (M30's `(-22 pips)`
  annotation keeps its minus sign after normalization, which stops the
  zone; M27 has no annotation). TP: regex rules (M27 colon-labeled
  ordinals, M30 plain label); common.tp.number excluded — the `TP1`
  ordinal digit must not become a phantom TP value.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET, NUMBER_PATTERN

PROVIDER_017_RULE_SET: dict[str, object] = {
    "name": "provider_017",
    "parent": "common",
    "overrides": [],
    "exclusions": ["common.tp.number", "common.condition.at_price"],
    "rules": [
        {
            "id": "p017.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p017.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p017.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p017.entry.at",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {"keywords": ["BUY", "SELL"], "requires_symbol": True},
            },
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["AT"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p017.tp.ordinal",
            "category": "TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"TP\d\s*:\s*({NUMBER_PATTERN})",
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
            "id": "p017.tp.labeled",
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
            "occurrence": "ALL",
        },
        {
            "id": "p017.trigger.now",
            "category": "ENTRY_TRIGGER",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"\b(NOW)\b",
                    "ignore_case": True,
                    "group": 1,
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
        {
            "id": "p017.action.move_sl_at",
            "category": "ACTION_MOVE_SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": rf"MOVE\s+SL\s+AT\s+({NUMBER_PATTERN})",
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

PROVIDER_017: dict[str, object] = {
    "provider_name": "provider_017",
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
    "rule_set": PROVIDER_017_RULE_SET,
    "symbol_aliases": [
        ["GOLD", "XAUUSD"],
        ["XAUUSD", "XAUUSD"],
        ["GBPCHF", "GBPCHF"],
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
