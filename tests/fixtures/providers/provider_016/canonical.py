"""Real corpus fixtures for provider_016 — @-separated signal levels.

VERBATIM excerpts from docs/corpus/real-messages.md (M23, M26, lines
282-307). Owner-supplied real provider messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "m23_at_separator_levels",
        "raw_text": (
            "(Use Proper Risk Management)\n"
            "\n"
            "Sell XAGUSD @ 65.1950\n"
            "SL @ 67.0731\n"
            "TP @ 61.3857"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAGUSD",
            "ENTRY": "65.1950",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "67.0731",
            "TP": ["61.3857"],
        },
    },
    {
        "name": "m26_at_entry_ordinal_tps",
        "raw_text": "Sell Gold @ 4103.210\nSL 4112.757\nTp1 4079.387\nTp2 4058.731",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4103.210",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "4112.757",
            "TP": ["4079.387", "4058.731"],
        },
    },
)
