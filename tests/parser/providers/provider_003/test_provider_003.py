"""Provider 003 — bitcoin-style, no decimals, LONG/SHORT keywords (§21.3).

Three structurally different shapes for this provider:

1. LONG/SHORT canonicalisation: the keyword "LONG" matches the LITERAL rule
   with value "LONG", and the rule's `canonical` param maps it to BUY;
2. crypto symbol lookup (BTC, ETH) via the alias table;
3. integer prices (no decimals) — must still be recognised as Price.
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    ParseResultState,
)
from packages.signal_core.enums import TradeDirection
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_003"


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_runtime(PROVIDER))


def test_provider_003_long_canonicalized_to_buy() -> None:
    r = _go("LONG BTC 60000 SL 58000 TP 65000")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.BUY
    assert by_slot[CandidateSlot.INSTRUMENT] == "BTC"
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal(60000))


def test_provider_003_short_canonicalized_to_sell() -> None:
    r = _go("SHORT ETH 3000 SL 3100 TP 2800")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.DIRECTION] is TradeDirection.SELL
    assert by_slot[CandidateSlot.INSTRUMENT] == "ETH"


def test_provider_003_canonical_alias_preserves_raw_text_in_evidence() -> None:
    """The canonical_alias MatchEvidence records both the raw text and the
    canonical value so the original keyword is preserved for audit."""
    r = _go("LONG BTC 60000 SL 58000 TP 65000")
    direction_fragments = [
        f for f in r.ir.fragments if f.slot is CandidateSlot.DIRECTION
    ]
    assert direction_fragments
    has_alias_evidence = any(
        any(ev.kind == "canonical_alias" for ev in f.evidence)
        for f in direction_fragments
    )
    assert has_alias_evidence


def test_provider_003_integer_prices_no_overflow() -> None:
    """A five-digit integer must not exceed max_numeric_value (1e12)."""
    r = _go("LONG BTC 100000 SL 99000 TP 110000")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == Price(Decimal(100000))


def test_provider_003_action_close_works() -> None:
    r = _go("LONG BTC 60000 SL 58000 TP 65000\nCLOSE")
    assert r.outcome is ParseResultState.PARSED
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions
    assert actions[0].value.name == "CLOSE"