"""Common base RuleSet shared by provider profiles (design §12.1).

Generic signal/action/trigger/condition rules inherited by every provider
via the §12.5 single-parent chain. Provider-specific syntax differences
are handled by provider-level rules and overrides, never by editing this
set for one provider.
"""

from __future__ import annotations

NUMBER_PATTERN = r"\d{1,13}(?:\.\d{1,12})?"

COMMON_RULE_SET: dict[str, object] = {
    "name": "common",
    "parent": None,
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "common.sl.number",
            "category": "SL",
            "matcher": {"kind": "NUMBER"},
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["SL"]},
            "constraints": [],
            "target": "SL",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "common.tp.number",
            "category": "TP",
            "matcher": {"kind": "NUMBER"},
            "scope": {"kind": "AFTER_TOKEN", "anchors": ["TP"]},
            "constraints": ["REPEATABLE"],
            "target": "TP",
            "priority": 10,
            "occurrence": "ALL",
        },
        {
            "id": "common.trigger.limit",
            "category": "ENTRY_TRIGGER",
            "matcher": {"kind": "LITERAL", "params": {"value": "LIMIT"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ENTRY_TRIGGER",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "common.trigger.stop",
            "category": "ENTRY_TRIGGER",
            "matcher": {"kind": "LITERAL", "params": {"value": "STOP"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ENTRY_TRIGGER",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "common.trigger.market",
            "category": "ENTRY_TRIGGER",
            "matcher": {"kind": "LITERAL", "params": {"value": "MARKET"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ENTRY_TRIGGER",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            # §8.1 CLOSE is an executable instruction only in imperative
            # contexts. Real corpus evidence (M16 "TP1 HIT", M32 "SIGNAL
            # COMPLETED ... MANUALLY CLOSE WITH 1150 PIPS") shows completion
            # markers turn "close" into an EVENT/REPORT statement, not an
            # instruction ("PIPS" marks pip-count profit reporting, M32;
            # commentary modality markers "should/maybe/consider" are the
            # same). The rule is REGEX (not LITERAL)
            # because LITERAL keyword-token candidates bypass constraint
            # checks — a REGEX site is constraint-checked. FORBIDS makes
            # close suppression the safe default in those contexts;
            # enabling it there requires provider evidence. Suppressed
            # closes are the non-executable side of the ambiguity (§14).
            "id": "common.action.close",
            "category": "ACTION_CLOSE",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"\b(CLOSE)\b",
                    "ignore_case": True,
                    "group": 1,
                    "keywords": [
                        "COMPLETED",
                        "HIT",
                        "DONE",
                        "PIPS",
                        "SHOULD",
                        "MAYBE",
                        "CONSIDER",
                    ],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["FORBIDS"],
            "target": "ACTION",
            "priority": 30,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.close_half",
            "category": "ACTION_PARTIAL_CLOSE",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": r"CLOSE\s+HALF", "ignore_case": True},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.close_percent",
            "category": "ACTION_PARTIAL_CLOSE",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": r"CLOSE\s+(\d{1,3})\s*%", "group": 1},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.breakeven_phrase",
            "category": "ACTION_BREAKEVEN",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"MOVE\s+SL\s+TO\s+(?:BE|BREAKEVEN|ENTRY)",
                    "ignore_case": True,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.remove_sl",
            "category": "ACTION_REMOVE_SL",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": r"REMOVE\s+SL", "ignore_case": True},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.move_sl",
            "category": "ACTION_MOVE_SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"(?:CHANGE\s+)?SL\s+(\d{1,13}(?:\.\d{1,12})?)",
                    "group": 1,
                    "keywords": ["BUY", "SELL", "LONG", "SHORT"],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["FORBIDS"],
            "target": "ACTION",
            "priority": 25,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.move_tp",
            "category": "ACTION_MOVE_TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"CHANGE\s+TP(?:\s+TO)?\s+(\d{1,13}(?:\.\d{1,12})?)",
                    "group": 1,
                    "keywords": ["BUY", "SELL", "LONG", "SHORT"],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["FORBIDS"],
            "target": "ACTION",
            "priority": 25,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.modify_entry",
            "category": "ACTION_MODIFY_ENTRY",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"CHANGE\s+ENTRY\s+TO\s+(\d{1,13}(?:\.\d{1,12})?)",
                    "group": 1,
                    "keywords": ["BUY", "SELL", "LONG", "SHORT"],
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": ["FORBIDS"],
            "target": "ACTION",
            "priority": 25,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.cancel_pending",
            "category": "ACTION_CANCEL",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": r"CANCEL\s+PENDING", "ignore_case": True},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "common.action.trigger_pending",
            "category": "ACTION_TRIGGER",
            "matcher": {
                "kind": "REGEX",
                "params": {"pattern": r"TRIGGER\s+PENDING", "ignore_case": True},
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 20,
            "occurrence": "FIRST",
        },
        {
            "id": "common.condition.at_price",
            "category": "CONDITION",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"\bAT\s+(\d{1,13}(?:\.\d{1,12})?)",
                    "group": 1,
                    "condition_kind": "AT_PRICE",
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "CONDITION",
            "priority": 30,
            "occurrence": "FIRST",
        },
    ],
}
