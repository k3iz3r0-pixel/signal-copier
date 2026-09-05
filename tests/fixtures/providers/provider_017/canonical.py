"""Real corpus fixtures for provider_017 — prose `at` entries and NOW wording.

VERBATIM excerpts from docs/corpus/real-messages.md (M16, M27, M30; lines
195-198, 309-327, 344-348). Owner-supplied real provider messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "m30_sell_now_at",
        "raw_text": (
            "GBPCHF - SELL NOW at 1.08280\n"
            "TP: 1.07750 (+53 pips)\n"
            "SL: 1.08500 (-22 pips)\n"
            "\n"
            "Don't risk more than 2% of your account size. Use position size "
            "calculator to calculate your risk!"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "GBPCHF",
            "ENTRY": "1.08280",
            "ENTRY_TRIGGER": "MARKET",
            "ENTRY_GEOMETRY": "MARKET",
            "SL": "1.08500",
            "TP": ["1.07750"],
        },
    },
    {
        "name": "m27_forecast_sell_limit",
        "raw_text": (
            "#EURUSD BEARISH🔽 FORECAST (This pair is ready)\n"
            "\n"
            "Overview & Confirmations: We discussed about this pair on the "
            "last video analysis, and it broke the trendline zone, after "
            "several retest and fails to come back up, this could be the "
            "final retest before the actual drop.\n"
            "\n"
            "Risk: Medium.\n"
            "\n"
            "Entry & Targets: \n"
            "\n"
            "I'm opening a SELL LIMIT now at 1.17725 \n"
            "\n"
            "TP1: 1.17350\n"
            "\n"
            "TP2:  1.16700\n"
            "\n"
            "SL: 1.17825\n"
            "\n"
            "https://www.tradingview.com/x/r75XMkTf/\n"
            "\n"
            "This analysis/trade does not constitute an investment advice, "
            "instead this is a trade that we've taken on our personal "
            "account and is shared on the solely purpose of journaling our "
            "performance and to provide educational content to our students, "
            "we are not responsible for any losses! Using risk managements "
            "is extremely important"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "EURUSD",
            "ENTRY": "1.17725",
            "ENTRY_TRIGGER": "LIMIT",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "1.17825",
            "TP": ["1.17350", "1.16700"],
        },
    },
    {
        "name": "m16_move_sl_at_follow_up",
        "raw_text": "GOLD - TP1 HIT ✅\n100+ Pips Profit Running ✅✅\n\n**Move SL at 4420**",
        "outcome": "PARSED",
        "fragments": {
            "INSTRUMENT": "XAUUSD",
            "ACTION": "MOVE_SL",
        },
    },
)
