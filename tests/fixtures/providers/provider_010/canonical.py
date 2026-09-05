"""Canonical signals for provider_010 — unusual field ordering (INFERENCE).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "sl_tp_before_entry",
        "raw_text": "BUY SL 1.0950 TP 1.1100 EURUSD 1.1000",
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
        "name": "tp_first",
        "raw_text": "TP 1.2400 SELL EURUSD 1.2500 SL 1.2550",
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
        "name": "symbol_last_no_adjacent_entry",
        "raw_text": "BUY 1.1000 SL 1.0950 TP 1.1100 EURUSD",
        "outcome": "PARTIAL",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
)
