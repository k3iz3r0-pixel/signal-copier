"""Canonical signals for provider_004 — PARSED / MALFORMED outcomes.

Each entry maps a raw input to the expected semantic output. These are
synthetic representations of the §21.4 emoji-marker family; they are NOT
verbatim copies of any real provider's messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "buy_emoji_marker",
        "raw_text": "\U0001f7e2 BUY #EURUSD\n\U0001f3af 1.1000\n\U0001f6d1 1.0950\n\U0001f4b0 1.1100",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
    {
        "name": "sell_two_tp_levels",
        "raw_text": "\U0001f534 SELL #EURUSD\n\U0001f3af 1.2500\n\U0001f6d1 1.2550\n\U0001f4b0 1.2400\n\U0001f4b0 1.2350",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.2500",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.2550",
            "TP": ["1.2400", "1.2350"],
        },
    },
    {
        "name": "conflicting_entry_markers",
        "raw_text": "\U0001f7e2 BUY #EURUSD\n\U0001f3af 1.1000\n\U0001f3af 1.1050\n\U0001f6d1 1.0950\n\U0001f4b0 1.1100",
        "outcome": "MALFORMED",
        "conflicts": ["ENTRY"],
    },
    {
        "name": "percent_sl_never_a_price",
        "raw_text": "\U0001f7e2 BUY #EURUSD\n\U0001f3af 1.1000\n\U0001f6d1 2%\n\U0001f4b0 1.1100",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "TP": ["1.1100"],
        },
        "note": "SL unresolved: '2%' is disqualified as a price operand",
    },
)
