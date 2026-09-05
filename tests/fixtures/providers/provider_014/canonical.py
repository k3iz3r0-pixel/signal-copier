"""Real corpus fixtures for provider_014 — core one-liners/labeled levels.

VERBATIM excerpts from docs/corpus/real-messages.md (M5, M6, M9-M13, M17,
M21, M22, M24, M25, M31). Owner-supplied real provider messages.
"""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "m12_slash_range_three_tps",
        "raw_text": "XAUUSD BUY 4267/4270\n\nSL 4257\n\nTp 4278\nTp 4290\nTp 4300",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4267/4270",
            "ENTRY_GEOMETRY": "RANGE",
            "SL": "4257",
            "TP": ["4278", "4290", "4300"],
        },
    },
    {
        "name": "m13_slash_range_sell",
        "raw_text": "XAUUSD SELL 4066/4070\n\nSL 4097\n\nTp 4055\nTp 4040\nTp 4020\nTo open",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4066/4070",
            "ENTRY_GEOMETRY": "RANGE",
            "SL": "4097",
            "TP": ["4055", "4040", "4020"],
        },
    },
    {
        "name": "m9_labeled_levels_repeated_take_profit",
        "raw_text": (
            "XAUUSD\n"
            "\n"
            "Personally, I’m primarily looking for longs at the moment. Granted, "
            "we’ve seen further escalation in the Middle East; however, the "
            "300/250 region has continued to hold well as our previous "
            "range-bound zone / holding the session relapse.\n"
            "\n"
            "This is a very aggressive entry, so I’m keeping risk lower and "
            "giving the setup room to play out.\n"
            "\n"
            "These are the key levels I’m trading off:\n"
            "\n"
            "Buy limit\n"
            "\n"
            "Entry: 4302.00\n"
            "Stop loss: 4273.00\n"
            "Take profit: 4320.00\n"
            "Take profit: 4375.00\n"
            "Take profit: 4525.00\n"
            "\n"
            "https://www.tradingview.com/x/g1ztcIRf/"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4302.00",
            "ENTRY_TRIGGER": "LIMIT",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "4273.00",
            "TP": ["4320.00", "4375.00", "4525.00"],
        },
    },
    {
        "name": "m10_core_adjacency_colon_labels",
        "raw_text": "USDJPY BUY 159.31\n\nSL:  158.81\nTP:  160.81\n--Trade by William",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "USDJPY",
            "ENTRY": "159.31",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "158.81",
            "TP": ["160.81"],
        },
    },
    {
        "name": "m11_repeated_unlabeled_tp",
        "raw_text": "XAUUSD SELL  4596.00\nTP 4592\nTP 4588\nTP 4581\nTP 4560\nSL 4601",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4596.00",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "4601",
            "TP": ["4592", "4588", "4581", "4560"],
        },
    },
    {
        "name": "m17_two_line_core",
        "raw_text": "GOLD\nBUY 4425",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4425",
            "ENTRY_GEOMETRY": "SINGLE",
        },
    },
    {
        "name": "m21_one_liner_limit_no_tp",
        "raw_text": "XAUUSD buy limit 4342.72 sl 4324.74",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4342.72",
            "ENTRY_TRIGGER": "LIMIT",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "4324.74",
        },
    },
    {
        "name": "m22_no_entry_stop_loss_label",
        "raw_text": "SELL US30\nStop Loss: 52953.2\n\nTake Profit : 52755.4\nTake Profit : 52625.1",
        "outcome": "PARTIAL",
        "unresolved_fields": ["ENTRY", "ENTRY_GEOMETRY", "ENTRY_TRIGGER"],
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "US30",
            "SL": "52953.2",
            "TP": ["52755.4", "52625.1"],
        },
    },
    {
        "name": "m24_sell_now_market",
        "raw_text": (
            "XAUUSD sell now 4133.00\n\nTp 4076.00\n\nSl 4152.00\n\n"
            "Ensure proper risk management‼️\n\nRisk 1% per trade"
        ),
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAUUSD",
            "ENTRY": "4133.00",
            "ENTRY_TRIGGER": "MARKET",
            "ENTRY_GEOMETRY": "MARKET",
            "SL": "4152.00",
            "TP": ["4076.00"],
        },
    },
    {
        "name": "m25_no_entry_gold",
        "raw_text": "Sell Gold\n\nSL: 4168.00\nTP: 4088.00",
        "outcome": "PARTIAL",
        "unresolved_fields": ["ENTRY", "ENTRY_GEOMETRY", "ENTRY_TRIGGER"],
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "XAUUSD",
            "SL": "4168.00",
            "TP": ["4088.00"],
        },
    },
    {
        "name": "m31_core_emoji_annotations",
        "raw_text": "🚀 BUY AUDJPY 100.814\n\n◾️SL 100.564(-25pips)\n◾️TP 101.064(+25pips)\n\n@Sp25PIPS ✊",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "AUDJPY",
            "ENTRY": "100.814",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "100.564",
            "TP": ["101.064"],
        },
    },
    {
        "name": "m6_commentary_no_signal",
        "raw_text": (
            "Since price might go back to  the marked supply zone and touches "
            "our BE, you can set your stoploss on 0.5% risk again if you can "
            "take the risk.\n"
            "\n"
            "• Decide based on your risk management"
        ),
        "outcome": "NO_SIGNAL",
        "fragments": {},
    },
)
