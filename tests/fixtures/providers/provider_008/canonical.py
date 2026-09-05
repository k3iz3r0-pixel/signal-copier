"""Canonical signals for provider_008 — colon key-value tables (INFERENCE).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "buy_pipe_table",
        "raw_text": "Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | TP: 1.1100",
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
        "name": "sell_line_per_field",
        "raw_text": "Pair: EURUSD\nSide: SELL\nEntry: 1.2500\nSL: 1.2550\nTP: 1.2400",
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
        "name": "duplicate_entry_conflict",
        "raw_text": "Pair: EURUSD | Side: BUY | Entry: 1.1000 | Entry: 1.1050 | SL: 1.0950 | TP: 1.1100",
        "outcome": "MALFORMED",
        "conflicts": ["ENTRY"],
    },
    {
        "name": "missing_entry_partial",
        "raw_text": "Pair: EURUSD | Side: BUY | SL: 1.0950 | TP: 1.1100",
        "outcome": "PARTIAL",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
)
