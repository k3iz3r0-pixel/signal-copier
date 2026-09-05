"""Canonical signals for provider_006 — pending-order family (§21.8).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "pending_buy_limit",
        "raw_text": "PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100",
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
        "name": "pending_sell_stop",
        "raw_text": "PENDING SELL STOP EURUSD 1.2500 SL 1.2550 TP 1.2400",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.2500",
            "ENTRY_TRIGGER": "STOP",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.2550",
            "TP": ["1.2400"],
        },
    },
    {
        "name": "ambiguous_triggers",
        "raw_text": "PENDING BUY LIMIT MARKET EURUSD 1.1000 SL 1.0950 TP 1.1100",
        "outcome": "AMBIGUOUS",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.1000",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
    {
        "name": "conflicting_directions",
        "raw_text": "PENDING BUY SELL EURUSD 1.1000 SL 1.0950 TP 1.1100",
        "outcome": "MALFORMED",
        "conflicts": ["DIRECTION"],
    },
    {
        "name": "at_form_without_sl_partial",
        "raw_text": "PENDING BUY LIMIT EURUSD @ 1.1000",
        "outcome": "PARTIAL",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY_TRIGGER": "LIMIT",
        },
        "note": "'@' breaks core adjacency; the number is left unbound",
    },
)
