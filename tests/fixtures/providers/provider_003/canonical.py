"""Canonical signals for provider_003 (bitcoin-style, LONG/SHORT)."""

from __future__ import annotations

EXAMPLES: tuple[dict[str, object], ...] = (
    {
        "name": "long_btc",
        "raw_text": "LONG BTC 60000 SL 58000 TP 65000",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "BTC",
            "ENTRY": "60000",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "58000",
            "TP": ["65000"],
        },
        "evidence": [
            {"kind": "canonical_alias", "raw": "LONG", "canonical": "BUY"},
        ],
    },
    {
        "name": "short_eth",
        "raw_text": "SHORT ETH 3000 SL 3100 TP 2800",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "SELL",
            "INSTRUMENT": "ETH",
            "ENTRY": "3000",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "3100",
            "TP": ["2800"],
        },
        "evidence": [
            {"kind": "canonical_alias", "raw": "SHORT", "canonical": "SELL"},
        ],
    },
    {
        "name": "long_btc_5digit",
        "raw_text": "LONG BTC 100000 SL 99000 TP 110000",
        "outcome": "PARSED",
        "fragments": {
            "DIRECTION": "BUY",
            "INSTRUMENT": "BTC",
            "ENTRY": "100000",
            "ENTRY_GEOMETRY": "SINGLE",
            "SL": "99000",
            "TP": ["110000"],
        },
    },
)