"""Canonical signals for provider_007 — ordinal TP-label family (INFERENCE).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "buy_two_labeled_tps",
        "raw_text": "BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.0950",
            "TP": ["1.1100", "1.1200"],
        },
    },
    {
        "name": "sell_three_labeled_tps",
        "raw_text": "SELL EURUSD 1.2500 TP1 1.2400 TP2 1.2300 TP3 1.2200 SL 1.2550",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.2500",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.2550",
            "TP": ["1.2400", "1.2300", "1.2200"],
        },
    },
    {
        "name": "reordered_fields",
        "raw_text": "BUY EURUSD 1.1000 SL 1.0950 TP1 1.1100 TP2 1.1200",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "SL": "1.0950",
            "TP": ["1.1100", "1.1200"],
        },
    },
    {
        "name": "two_numbers_before_first_tp_conflict",
        "raw_text": "BUY EURUSD 1.1000 1.1050 TP1 1.1100 TP2 1.1200 SL 1.0950",
        "outcome": "MALFORMED",
        "conflicts": ["ENTRY"],
    },
    {
        "name": "no_entry_partial",
        "raw_text": "BUY EURUSD TP1 1.1100 TP2 1.1200 SL 1.0950",
        "outcome": "PARTIAL",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "SL": "1.0950",
            "TP": ["1.1100", "1.1200"],
        },
    },
)
