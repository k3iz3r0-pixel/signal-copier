"""Test-only profile for the multi-block engine (ADR 0013, Phase 2E).

This is NOT a provider onboarding: it is the minimal test harness that
declares section dividers (profile-declared data, engine-generic) so the
engine's multi-block path can be exercised against corpus-shaped messages.
Production families declare ``section_dividers`` only at onboarding time.
"""

from __future__ import annotations

from packages.parser.profiles import ProfileRuntime, load_profile
from packages.parser_profiles.data.common import COMMON_RULE_SET, NUMBER_PATTERN

MULTIBLOCK_PROFILE: dict[str, object] = {
    "provider_name": "test_multiblock",
    "version": "2B",
    "capabilities": {
        "close_full": True,
        "close_half": True,
        "profit_close": True,
        "move_sl_breakeven": True,
        "remove_sl": True,
        "cancel_pending": True,
        "trigger_pending": True,
        "move_sl_number": True,
        "move_sl_conditional": True,
        "move_tp_conditional": True,
        "move_entry_conditional": True,
        "edit_handling": True,
        "delete_handling": True,
        "reply_required": True,
        "negative_keywords": True,
        "last_signal_execution": True,
        "trailing": True,
        "multi_signal": True,
        "multi_message": True,
    },
    "rule_set": {
        "name": "test_multiblock",
        "parent": "common",
        "overrides": [],
        "exclusions": ["common.sl.number", "common.tp.number"],
        "rules": [
            {
                "id": "mb.direction",
                "category": "DIRECTION",
                "matcher": {
                    "kind": "REGEX",
                    "params": {
                        "pattern": r"\b(BUY|SELL)\b",
                        "ignore_case": True,
                        "group": 1,
                    },
                },
                "scope": {"kind": "WHOLE_MESSAGE"},
                "constraints": [],
                "target": "DIRECTION",
                "priority": 10,
                "occurrence": "FIRST",
            },
            {
                "id": "mb.instrument",
                "category": "INSTRUMENT",
                "matcher": {"kind": "SYMBOL"},
                "scope": {"kind": "WHOLE_MESSAGE"},
                "constraints": [],
                "target": "INSTRUMENT",
                "priority": 10,
                "occurrence": "FIRST",
            },
            {
                "id": "mb.entry",
                "category": "ENTRY",
                "matcher": {
                    "kind": "REGEX",
                    "params": {
                        "pattern": rf"Entry\s*:\s*({NUMBER_PATTERN})",
                        "ignore_case": True,
                        "group": 1,
                    },
                },
                "scope": {"kind": "WHOLE_MESSAGE"},
                "constraints": [],
                "target": "ENTRY",
                "priority": 15,
                "occurrence": "FIRST",
            },
            {
                "id": "mb.sl",
                "category": "SL",
                "matcher": {
                    "kind": "REGEX",
                    "params": {
                        "pattern": rf"SL\s*:\s*({NUMBER_PATTERN})",
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
                "id": "mb.tp",
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
                "constraints": ["REPEATABLE"],
                "target": "TP",
                "priority": 10,
                "occurrence": "ALL",
            },
        ],
    },
    "symbol_aliases": [
        ["XAUUSD", "XAUUSD"],
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
    "section_dividers": ["⸻"],
}


def make_mb_runtime() -> ProfileRuntime:
    return load_profile(MULTIBLOCK_PROFILE, {"common": COMMON_RULE_SET})
