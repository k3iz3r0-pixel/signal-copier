"""Real corpus fixtures for provider_015 — labeled scalp cards.

VERBATIM excerpts from docs/corpus/real-messages.md (M7, M8, lines 71-117).
Owner-supplied real provider messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "m7_bought_long_card",
        "raw_text": (
            "💭 Trade ID #300\n"
            "\n"
            "Pair : EURUSD\n"
            "Direction : 🔼 Long\n"
            "Trade Type: Scalp\n"
            "―――――――――――――――\n"
            "FXG BOUGHT EURUSD at 1.16122\n"
            "\n"
            "SL 1.16112 [1 Pips]\n"
            "TP1 1.16132 [1R]\n"
            "TP2 1.16147 [2.5R]\n"
            "TP3 1.16172 [5R]\n"
            "―――――――――――――――\n"
            "Accuracy : ±78% - Verified\n"
            "Position Size: 2% [1.0% for Props]\n"
            "$1K Risk Lot Size : 100 Lots\n"
            "―――――――――――――――\n"
            "\n"
            "🌐 ForexGran.Com ✌ 💲\n"
            "\n"
            "🕯 Small steps lead to big gains over time 🕯"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.16122",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.16112",
            "TP": ["1.16132", "1.16147", "1.16172"],
        },
    },
    {
        "name": "m8_sold_short_card",
        "raw_text": (
            "💭 Trade ID #298\n"
            "\n"
            "Pair : EURUSD\n"
            "Direction : 🔽 Short\n"
            "Trade Type: Scalp\n"
            "―――――――――――――――\n"
            "FXG SOLD EURUSD at 1.16186\n"
            "\n"
            "SL 1.16233 [4.7 Pips]\n"
            "TP1 1.16153 [0.7R]\n"
            "TP2 1.16068 [2.5R]\n"
            "TP3 1.15951 [5R]\n"
            "―――――――――――――――\n"
            "Accuracy : ±78% - Verified\n"
            "Position Size: 2% [1.0% for Props]\n"
            "$1K Risk Lot Size : 21.28 Lots\n"
            "―――――――――――――――\n"
            "\n"
            "🌐 ForexGran.Com ✌ 💲\n"
            "\n"
            "🕯 Small steps lead to big gains over time 🕯"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.16186",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.16233",
            "TP": ["1.16153", "1.16068", "1.15951"],
        },
    },
)
