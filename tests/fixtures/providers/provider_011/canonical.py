"""Canonical signals for provider_011 — lot/quantity family (INFERENCE).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "fractional_lots",
        "raw_text": "BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100",
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
        "name": "integer_lots",
        "raw_text": "SELL EURUSD 2 LOTS @ 1.2500 SL 1.2550 TP 1.2400",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.2500",
            "SL": "1.2550",
            "TP": ["1.2400"],
        },
    },
    {
        "name": "double_entry_conflict",
        "raw_text": "BUY EURUSD 0.5 LOTS @ 1.1000 1.1010 SL 1.0950 TP 1.1100",
        "outcome": "MALFORMED",
        "conflicts": ["ENTRY"],
    },
    {
        "name": "no_lots_at_form",
        "raw_text": "BUY EURUSD @ 1.1000 SL 1.0950 TP 1.1100",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
)
