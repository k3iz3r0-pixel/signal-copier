"""Real corpus fixtures for provider_013 — bracket-annotated ticket blocks.

VERBATIM excerpts from docs/corpus/real-messages.md (M1-M4, lines 1-48).
These are the owner-supplied real provider messages, not synthetic ones.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "m2_new_order_signal",
        "raw_text": (
            "NEW ORDER - XAUUSD Sell 📉\n"
            "# 508432522\n"
            "\n"
            "----------{ NEW }----------\n"
            "Entry: 2656.00 [Lots: 2.50]\n"
            "SL:    2659.99 [39.9 Pips]\n"
            "TP:    2647.79 [82.1 Pips]\n"
            "RR:    2.06\n"
            "---------------------------"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "2656.00",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "2659.99",
            "TP": ["2647.79"],
        },
    },
    {
        "name": "m1_closed_event",
        "raw_text": (
            "🔴 CLOSED - XAUUSD Sell 🔴\n"
            "# 508432522\n"
            "\n"
            "{ CLOSED }-\n"
            "Entry:  2656.00\n"
            "Exit:   2659.99\n"
            "Profit: -1 015$\n"
            "-\n"
            "⏱ Duration: 0h 17m 31s \n"
            "⭕ Closed due to Stoploss"
        ),
        "outcome": "NO_SIGNAL",
        "fragments": {"INSTRUMENT": "XAUUSD"},
    },
    {
        "name": "m3_weekly_report",
        "raw_text": (
            "♻ Weekly Report ♻\n"
            "\n"
            "🟢 XAUUSD Buy\u00a0\u00a0\u00a0 1.7%\n"
            "🔴 XAUUSD Buy\u00a0\u00a0\u00a0\u00a0 -1%\n"
            "🔴 XAUUSD Buy\u00a0\u00a0\u00a0\u00a0 -1%\n"
            "🔴 XAUUSD Buy\u00a0\u00a0\u00a0\u00a0 -1%\n"
            "🔴 XAUUSD Buy\u00a0\u00a0\u00a0\u00a0 -1%\n"
            "🔴 XAUUSD Sell\u00a0\u00a0\u00a0 -1%\n"
            "\n"
            "Profit: -3,300 (-3.3%)\n"
            "Wins: 1\u00a0\u00a0 Losses: 5\u00a0\u00a0 BE: 0\n"
            "\n"
            "https://t.me/NeoGoldT"
        ),
        "outcome": "NO_SIGNAL",
        "fragments": {"INSTRUMENT": "XAUUSD"},
    },
    {
        "name": "m4_moved_sl_action",
        "raw_text": (
            "🛠 XAUUSD Buy - Modified\n"
            "\n"
            "# 506633067\n"
            "-------{ Moved SL }--------\n"
            "🗑 Old SL: 2723.94\n"
            "👉 New SL: 2726.94\n"
            "---------------------------\n"
            "Stop moved to Breakeven"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "XAUUSD",
            "ACTION": "MOVE_SL",
        },
    },
)
