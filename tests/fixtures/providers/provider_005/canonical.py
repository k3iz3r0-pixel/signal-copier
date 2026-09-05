"""Canonical signals for provider_005 — PARSED / PARTIAL outcomes.

Synthetic representations of the §21.7 numbered-levels family; NOT verbatim
copies of any real provider's messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "design_example_no_symbol",
        "raw_text": "SCALP LONG\n1) 3350\n2) 3340\n3) 3330\nSL 3300\nTP 3400",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "ENTRY": ["3350", "3340", "3330"],
            "ENTRY_GEOMETRY": "MULTIPLE",
            "SL": "3300",
            "TP": ["3400"],
        },
        "note": "INSTRUMENT unresolved — the design example carries no symbol",
    },
    {
        "name": "with_symbol_two_levels",
        "raw_text": "SCALP LONG EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": ["3350", "3340"],
            "ENTRY_GEOMETRY": "MULTIPLE",
            "SL": "3300",
            "TP": ["3400"],
        },
    },
    {
        "name": "prose_noise_and_date_chain",
        "raw_text": "SCALP LONG EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400\ndated 2026-09-05",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": ["3350", "3340"],
            "SL": "3300",
            "TP": ["3400"],
        },
    },
    {
        "name": "levels_only_partial",
        "raw_text": "SCALP LONG EURUSD\nSL 3300\nTP 3400",
        "outcome": "PARTIAL",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "SL": "3300",
            "TP": ["3400"],
        },
    },
)
