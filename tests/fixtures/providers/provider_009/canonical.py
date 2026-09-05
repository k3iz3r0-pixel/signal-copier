"""Canonical signals for provider_009 — prose synonym family (INFERENCE).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "long_canonical_casing",
        "raw_text": "Long EURUSD 1.1000. Stop 1.0950. Target 1.1100.",
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
        "name": "short_prose_lowercase",
        "raw_text": "We go short EURUSD 1.2500 stop 1.2550 target 1.2400 now",
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
        "name": "mixed_direction_conflict",
        "raw_text": "Long EURUSD 1.1000. Stop 1.0950. Target 1.1100. Short EURUSD 1.1500.",
        "outcome": "MALFORMED",
        "conflicts": ["DIRECTION", "ENTRY"],
    },
    {
        "name": "entry_preposition_partial",
        "raw_text": "Long EURUSD at 1.1000. Stop 1.0950. Target 1.1100.",
        "outcome": "PARTIAL",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "SL": "1.0950",
            "TP": ["1.1100"],
        },
    },
)
