"""Canonical messages for provider_012 — follow-up actions (INFERENCE).

Synthetic representations; NOT verbatim copies of any real provider's
messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "standalone_move_sl",
        "raw_text": "MOVE SL TO 1.0900",
        "outcome": "NO_SIGNAL",
        "fragments": {"ACTION": "MOVE_SL"},
    },
    {
        "name": "instrument_move_sl",
        "raw_text": "EURUSD MOVE SL 1.0900",
        "outcome": "PARSED",
        "fragments": {"INSTRUMENT": "EURUSD", "ACTION": "MOVE_SL"},
    },
    {
        "name": "move_tp",
        "raw_text": "MOVE TP TO 1.1300",
        "outcome": "PARSED",
        "fragments": {"ACTION": "MOVE_TP"},
    },
    {
        "name": "breakeven",
        "raw_text": "MOVE SL TO BE",
        "outcome": "PARSED",
        "fragments": {"ACTION": "BREAKEVEN"},
    },
    {
        "name": "conflicting_actions",
        "raw_text": "MOVE SL TO 1.0900 MOVE TP TO 1.1300",
        "outcome": "MALFORMED",
        "conflicts": ["ACTION"],
    },
)
