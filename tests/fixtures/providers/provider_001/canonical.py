"""Canonical signals for provider_001 — PARSED outcome.

Each entry maps a raw input to the expected semantic output. These are
synthetic representations of provider capability categories; they are
NOT verbatim copies of any real provider's messages.
"""

from __future__ import annotations

# raw input → expected outcome, slots
EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "buy_with_sl_tp",
        "raw_text": "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100",
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
        "name": "sell_with_sl_tp",
        "raw_text": "SELL EURUSD 1.2500 SL 1.2550 TP 1.2400",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.2500",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.2550",
            "TP": ["1.2400"],
        },
    },
    {
        "name": "entry_range",
        "raw_text": "BUY XAUUSD 2350-2360 SL 2340 TP 2400",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": {"range": ("2350", "2360")},
            "ENTRY_GEOMETRY": "RANGE",
            "SL": "2340",
            "TP": ["2400"],
        },
    },
    {
        "name": "pending_limit",
        "raw_text": "BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "ENTRY_TRIGGER": "LIMIT",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
    {
        "name": "pending_stop",
        "raw_text": "BUY STOP EURUSD 1.1000 SL 1.0950 TP 1.1100",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "ENTRY_TRIGGER": "STOP",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
    {
        "name": "multiple_tp",
        "raw_text": "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 TP 1.1150",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.0950",
            "TP": ["1.1100", "1.1150"],
        },
    },
)