"""Provider 011 — lot/quantity-bearing inline signals (INFERENCE).

Structural family: inline signals that carry a lot-size quantity before
the actual prices:

``BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100``

No §21 example carries a quantity; it is a synthetic member of the
false-positive-numeric axis: the lot number must NEVER become
ENTRY/SL/TP (§6/§7 numeric binding). No new semantics — the frozen
Phase 2A contract has no quantity field, so the lot size is preserved
as an unbound PRICE candidate (rejected semantics are never invented;
§16.4).

Engine mapping (no pipeline changes):
- Entry = the LAST number in the BEFORE_TOKEN SL zone (occurrence LAST):
  for the canonical form that zone is
  ``BUY EURUSD 0.5 LOTS @ 1.1000`` whose last number is the real entry.
  ``@`` is not glue, so the zone stops there — which is exactly why the
  entry rule must scan the whole zone, and why a plain core-adjacency
  entry rule would mis-bind ``0.5`` (it sits directly after the symbol).
- No whole-message entry rule exists in this profile, so no other
  number can silently become the entry.
"""

from __future__ import annotations

from .common import COMMON_RULE_SET

PROVIDER_011_RULE_SET: dict[str, object] = {
    "name": "provider_011",
    "parent": "common",
    "overrides": [],
    "exclusions": [],
    "rules": [
        {
            "id": "p011.direction.buy",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "BUY"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p011.direction.sell",
            "category": "DIRECTION",
            "matcher": {"kind": "LITERAL", "params": {"value": "SELL"}},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "DIRECTION",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p011.instrument",
            "category": "INSTRUMENT",
            "matcher": {"kind": "SYMBOL"},
            "scope": {"kind": "WHOLE_MESSAGE"},
            "constraints": [],
            "target": "INSTRUMENT",
            "priority": 10,
            "occurrence": "FIRST",
        },
        {
            "id": "p011.entry.last_before_sl",
            "category": "ENTRY",
            "matcher": {
                "kind": "NUMBER",
                "params": {
                    "keywords": ["BUY", "SELL"],
                    "requires_symbol": True,
                },
            },
            "scope": {"kind": "BEFORE_TOKEN", "anchors": ["SL"]},
            "constraints": ["REQUIRES"],
            "target": "ENTRY",
            "priority": 20,
            "occurrence": "LAST",
        },
    ],
}

PROVIDER_011: dict[str, object] = {
    "provider_name": "provider_011",
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
    "rule_set": PROVIDER_011_RULE_SET,
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
