"""Canonical signals for provider_002 (multiline, em-dash)."""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "multiline_buy",
        "raw_text": "BUY EURUSD\nENTRY 1.1000\nSL \u2014 1.0950\nTP \u2014 1.1100",
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
        "name": "multiline_sell",
        "raw_text": "SELL GBPJPY\nENTRY 150.00\nSL \u2014 151.00\nTP \u2014 148.00",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "GBPJPY",
            "ENTRY": "150.00",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "151.00",
            "TP": ["148.00"],
        },
    },
)