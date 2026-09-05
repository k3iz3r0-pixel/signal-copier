"""Actions for provider_001 — PARSED outcome with an ACTION_* fragment."""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "close_fully",
        "raw_text": "CLOSE",
        "outcome": "PARSED",
        "fragments": {"ACTION": "CLOSE"},
        "context": "LAST_SIGNAL",
    },
    {
        "name": "close_half",
        "raw_text": "CLOSE HALF",
        "outcome": "PARSED",
        "fragments": {"ACTION": "PARTIAL_CLOSE"},
    },
    {
        "name": "close_percent",
        "raw_text": "CLOSE 50%",
        "outcome": "PARSED",
        "fragments": {"ACTION": "PARTIAL_CLOSE"},
    },
    {
        "name": "breakeven",
        "raw_text": "MOVE SL TO BE",
        "outcome": "PARSED",
        "fragments": {"ACTION": "BREAKEVEN"},
    },
    {
        "name": "breakeven_long_form",
        "raw_text": "MOVE SL TO BREAKEVEN",
        "outcome": "PARSED",
        "fragments": {"ACTION": "BREAKEVEN"},
    },
    {
        "name": "remove_sl",
        "raw_text": "REMOVE SL",
        "outcome": "PARSED",
        "fragments": {"ACTION": "MOVE_SL"},
    },
    {
        "name": "cancel_pending",
        "raw_text": "CANCEL PENDING",
        "outcome": "PARSED",
        "fragments": {"ACTION": "CANCEL"},
    },
    {
        "name": "trigger_pending",
        "raw_text": "TRIGGER PENDING NOW",
        "outcome": "PARSED",
        "fragments": {"ACTION": "MODIFY"},
    },
    {
        "name": "change_tp",
        "raw_text": "CHANGE TP TO 1.1150",
        "outcome": "PARSED",
        "fragments": {"ACTION": "MOVE_TP"},
    },
)