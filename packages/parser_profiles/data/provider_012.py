"""Provider 012 — follow-up SL/TP modification actions (INFERENCE).

Structural family: update-style messages that move SL/TP levels of a
PREVIOUS signal rather than opening one:

``MOVE SL TO 1.0900``  /  ``EURUSD MOVE SL 1.0900``  /
``MOVE TP TO 1.1300``  /  ``MOVE SL TO BE``

Documented §20 semantics (not new): §20.13 Change SL (standalone MOVE_SL
without instrument → ``follow_up_only`` NO_SIGNAL + correlation
TARGET_LAST_SIGNAL; with instrument → PARSED action), §20.14 Change TP
→ MOVE_TP, §20.9 breakeven phrase. The common rules already cover
``CHANGE SL/TP/ENTRY TO x``, ``REMOVE SL``, ``CLOSE ...`` — this profile
adds only the ``MOVE SL|TP TO <number>`` phrasings.

Action-context suppression (``_fragments_from_winners``): the TP number
in ``MOVE SL TO 1.2500 TP 1.2600`` is preserved as a candidate but NOT
fragment-bound, because this family's rules do not declare direction
keywords — correct: an update message must not look like a new signal.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET

PROVIDER_012_RULE_SET: dict[str, object] = {
    "name": "provider_012",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p012.action.move_sl_to",
            "category": "ACTION_MOVE_SL",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"MOVE\s+SL\s+TO\s+(\d{1,13}(?:\.\d{1,12})?)",
                    "group": 1,
                },
            },
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "ACTION",
            "priority": 15,
            "occurrence": "FIRST",
        },
        {
            "id": "p012.action.move_tp_to",
            "category": "ACTION_MOVE_TP",
            "matcher": {
                "kind": "REGEX",
                "params": {
                    "pattern": r"MOVE\s+TP\s+TO\s+(\d{1,13}(?:\.\d{1,12})?)",
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

PROVIDER_012: dict[str, object] = {
    "provider_name": "provider_012",
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
    "rule_set": PROVIDER_012_RULE_SET,
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
