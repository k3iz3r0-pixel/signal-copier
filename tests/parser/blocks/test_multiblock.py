"""Multi-block message contract tests (ADR 0013, Phase 2E).

Covers: single-block legacy shape, two independent blocks, four-block
duplicate-feed messages (M19-style), mixed event/action/signal messages
(M20-style), two instruments, two directions, block-local conflicts,
cross-block non-merging, source-span correctness, determinism, and the
001-017 never-segment regression guard.
"""

from __future__ import annotations

import itertools
from decimal import Decimal

import pytest

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    FragmentState,
    ParseResultState,
)
from packages.parser.pipeline import normalize, tokenize
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw
from tests.parser.blocks._profile import make_mb_runtime

PROVIDER = "test_multiblock"

# Verbatim corpus texts (docs/corpus/real-messages.md M19 lines 215-247,
# M20 lines 251-267).
M19_CORPUS = (
    "Hello traders,\n\nThese are my first orders for today:\n\n⸻\n"
    "Please note:\n\nTrading involves risk and may not be suitable for "
    "everyone. This is not financial advice, just my personal opinion. "
    "Always trade responsibly.\n\n⸻\nInstrument: US30\n\nCronos Markets "
    "data:\nSELL STOP\nEntry: 53071\nSL: 53241 (-1700 pips)\nTP: 52995 "
    "(+760 pips)\n\nBUY STOP\nEntry: 53238\nSL: 53068 (-1700 pips)\nTP: "
    "53314 (+760 pips)\n⸻\nFunding Dynasty data:\nSELL STOP\nEntry: "
    "53071\nSL: 53241 (-1700 pips)\nTP: 52995 (+760 pips)\n\nBUY STOP\n"
    "Entry: 53238\nSL: 53068 (-1700 pips)\nTP: 53314 (+760 pips)\n"
)
M20_CORPUS = (
    "The sell stop order was triggered.\nDelete the buy stop order.\n\n"
    "I’ve placed a new buy stop:\n\n⸻\nCronos Markets data:\nBUY STOP "
    "Order\nEntry: 53241\nSL: 53071 (-1700 pips)\nTP: 53273 (+320 pips)\n"
    "⸻\nFunding Dynasty data:\nBUY STOP Order\nEntry: 53241\nSL: 53071 "
    "(-1700 pips)\nTP: 53273 (+320 pips)\n"
)

# Synthetic four-block duplicate-feed message (M19-style, feed sections
# only): two independent stop orders, each posted to two data feeds.
M19_STYLE_4 = (
    "Cronos Markets data:\nSELL STOP\nEntry: 53071\nSL: 53241\nTP: 52995\n\n"
    "BUY STOP\nEntry: 53238\nSL: 53068\nTP: 53314\n⸻\n"
    "Funding Dynasty data:\nSELL STOP\nEntry: 53071\nSL: 53241\nTP: 52995\n\n"
    "BUY STOP\nEntry: 53238\nSL: 53068\nTP: 53314\n"
)

# Synthetic mixed event/action/signal message (M20-style, sections
# separated by blank lines so event, action and signals are distinct
# blocks).
M20_STYLE_MIXED = (
    "The sell stop order was triggered.\n\nDelete the buy stop order.\n\n⸻\n"
    "Cronos Markets data:\nBUY STOP Order\nEntry: 53241\nSL: 53071\n"
    "TP: 53273\n⸻\nFunding Dynasty data:\nBUY STOP Order\nEntry: 53241\n"
    "SL: 53071\nTP: 53273\n"
)


def _go(text: str):
    return parse(make_raw(text), make_metadata(PROVIDER), make_mb_runtime())


def _fragment(block, slot):
    return next((f for f in block.ir.fragments if f.slot is slot), None)


def _parsed_indices(result) -> list[int]:
    return [
        i
        for i, b in enumerate(result.blocks or ())
        if b.outcome is ParseResultState.PARSED
    ]


# ---------------------------------------------------------------------------
# 1. one block (legacy single-unit shape preserved byte-for-byte)
# ---------------------------------------------------------------------------


def test_single_block_message_keeps_legacy_shape() -> None:
    text = "XAUUSD\nSELL\nEntry: 2400\nSL: 2410\nTP: 2380"
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    assert r.blocks is None


def test_trailing_divider_with_single_content_section_keeps_legacy_shape() -> None:
    text = "XAUUSD\nSELL\nEntry: 2400\nSL: 2410\nTP: 2380\n⸻\n"
    r = _go(text)
    assert r.blocks is None
    assert r.outcome is ParseResultState.PARSED


# ---------------------------------------------------------------------------
# 2. single newlines never split a section (intra-block adjacency kept)
# ---------------------------------------------------------------------------


def test_single_newlines_stay_inside_one_block() -> None:
    text = "Note:\n⸻\nXAUUSD\nSELL\nEntry: 2400\nSL: 2410\nTP: 2380\n"
    r = _go(text)
    assert r.blocks is not None and len(r.blocks) == 2
    signal_block = r.blocks[1]
    assert signal_block.outcome is ParseResultState.PARSED
    assert _fragment(signal_block, CandidateSlot.DIRECTION) is not None
    assert _fragment(signal_block, CandidateSlot.ENTRY).value == Price(Decimal(2400))
    assert _fragment(signal_block, CandidateSlot.SL).value == Price(Decimal(2410))
    assert _fragment(signal_block, CandidateSlot.TP).value == (Price(Decimal(2380)),)


# ---------------------------------------------------------------------------
# 3. two independent blocks (different instruments and directions)
# ---------------------------------------------------------------------------


def test_two_independent_blocks_multi_signal() -> None:
    text = (
        "⸻\nXAUUSD\nSELL\nEntry: 2400\nSL: 2410\nTP: 2380\n⸻\n"
        "EURUSD\nBUY\nEntry: 1.1000\nSL: 1.1050\nTP: 1.0950\n⸻\n"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    assert r.blocks is not None and len(r.blocks) == 2
    assert _parsed_indices(r) == [0, 1]
    assert all(b.duplicate_of is None for b in r.blocks)
    # anti-merge: the top-level IR carries no fragments
    assert r.ir.fragments == ()
    assert r.ir.conflicts == ()
    b0, b1 = r.blocks
    assert _fragment(b0, CandidateSlot.INSTRUMENT).value == "XAUUSD"
    assert _fragment(b0, CandidateSlot.DIRECTION).value is not None
    assert _fragment(b1, CandidateSlot.INSTRUMENT).value == "EURUSD"
    assert _fragment(b1, CandidateSlot.DIRECTION).value is not None
    # block isolation: each block carries exactly its own instrument
    assert _fragment(b0, CandidateSlot.INSTRUMENT).value != (
        _fragment(b1, CandidateSlot.INSTRUMENT).value
    )


# ---------------------------------------------------------------------------
# 4. four-block M19-style duplicate-feed message
# ---------------------------------------------------------------------------


def test_four_block_duplicate_feed_sections() -> None:
    r = _go(M19_STYLE_4)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    blocks = r.blocks
    # each feed header stays on a single newline with its first order, so
    # the message is four blocks: (header+SELL1, BUY1, header+SELL2, BUY2)
    assert blocks is not None and len(blocks) == 4
    assert _parsed_indices(r) == [0, 1, 2, 3]
    # duplicate feed copies are linked, originals are not
    assert blocks[0].duplicate_of is None
    assert blocks[1].duplicate_of is None
    assert blocks[2].duplicate_of == 0
    assert blocks[3].duplicate_of == 1
    # independent orders are never cross-marked
    assert blocks[1].duplicate_of != 0
    # per-block payloads
    assert _fragment(blocks[0], CandidateSlot.ENTRY).value == Price(Decimal(53071))
    assert _fragment(blocks[1], CandidateSlot.ENTRY).value == Price(Decimal(53238))
    assert _fragment(blocks[2], CandidateSlot.ENTRY).value == Price(Decimal(53071))
    assert _fragment(blocks[3], CandidateSlot.ENTRY).value == Price(Decimal(53238))
    assert r.ir.fragments == ()


# ---------------------------------------------------------------------------
# 5. verbatim corpus M19
# ---------------------------------------------------------------------------


def test_real_m19_corpus_message() -> None:
    r = _go(M19_CORPUS)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    blocks = r.blocks
    assert blocks is not None and len(blocks) == 9
    assert _parsed_indices(r) == [5, 6, 7, 8]
    assert blocks[7].duplicate_of == 5
    assert blocks[8].duplicate_of == 6
    assert blocks[5].duplicate_of is None
    assert blocks[6].duplicate_of is None
    for i in (5, 6, 7, 8):
        assert blocks[i].ir.conflicts == ()
        assert _fragment(blocks[i], CandidateSlot.DIRECTION) is not None
        assert _fragment(blocks[i], CandidateSlot.ENTRY) is not None
        assert _fragment(blocks[i], CandidateSlot.SL) is not None
        assert _fragment(blocks[i], CandidateSlot.TP) is not None
    assert _fragment(blocks[5], CandidateSlot.ENTRY).value == Price(Decimal(53071))
    assert _fragment(blocks[6], CandidateSlot.ENTRY).value == Price(Decimal(53238))
    # "Instrument: US30" section: no direction, no executable content
    assert blocks[4].outcome is ParseResultState.NO_SIGNAL
    assert r.ir.fragments == ()


# ---------------------------------------------------------------------------
# 6. verbatim corpus M20 (mixed events/actions/signals)
# ---------------------------------------------------------------------------


def test_real_m20_corpus_message() -> None:
    r = _go(M20_CORPUS)
    blocks = r.blocks
    assert blocks is not None and len(blocks) == 4
    # Block 0 keeps the two consecutive narrative lines (single newline):
    # "sell" and "buy" conflict INSIDE the block — escalated honestly.
    assert blocks[0].outcome is ParseResultState.MALFORMED
    assert any(c.slot is CandidateSlot.DIRECTION for c in blocks[0].ir.conflicts)
    # the conflict stays block-local
    assert r.ir.conflicts == ()
    assert blocks[1].outcome is ParseResultState.PARTIAL
    assert blocks[2].outcome is ParseResultState.PARSED
    assert blocks[3].outcome is ParseResultState.PARSED
    assert blocks[3].duplicate_of == 2
    # message escalates to MALFORMED (no silent execution)
    assert r.outcome is ParseResultState.MALFORMED
    assert _fragment(blocks[2], CandidateSlot.ENTRY).value == Price(Decimal(53241))
    assert _fragment(blocks[3], CandidateSlot.ENTRY).value == Price(Decimal(53241))


def test_m20_style_mixed_sections_separated() -> None:
    r = _go(M20_STYLE_MIXED)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    blocks = r.blocks
    assert blocks is not None and len(blocks) == 4
    # event and action sentences are non-executable partial blocks
    assert blocks[0].outcome is ParseResultState.PARTIAL
    assert blocks[1].outcome is ParseResultState.PARTIAL
    # no ACTION fragment exists anywhere (no cancel/delete rule fires)
    for b in blocks:
        assert _fragment(b, CandidateSlot.ACTION) is None
        assert b.ir.conflicts == ()
    assert blocks[2].outcome is ParseResultState.PARSED
    assert blocks[3].outcome is ParseResultState.PARSED
    assert blocks[3].duplicate_of == 2
    assert r.ir.fragments == ()


# ---------------------------------------------------------------------------
# 7. block-local conflict escalation without cross-block weakening
# ---------------------------------------------------------------------------


def test_block_local_conflict_escalates_message() -> None:
    text = "BUY now\nSELL now\n⸻\nXAUUSD\nEntry: 2400\n"
    r = _go(text)
    assert r.outcome is ParseResultState.MALFORMED
    blocks = r.blocks
    assert blocks is not None and len(blocks) == 2
    assert blocks[0].outcome is ParseResultState.MALFORMED
    assert any(c.slot is CandidateSlot.DIRECTION for c in blocks[0].ir.conflicts)
    assert blocks[1].outcome is ParseResultState.NO_SIGNAL
    assert blocks[1].ir.conflicts == ()
    # the clean block's parse is preserved and readable
    assert _fragment(blocks[1], CandidateSlot.INSTRUMENT).value == "XAUUSD"
    assert r.ir.conflicts == ()


# ---------------------------------------------------------------------------
# 8. cross-block non-merging
# ---------------------------------------------------------------------------


def test_cross_block_non_merging() -> None:
    text = "SELL signal\n⸻\nEntry: 2400\nSL: 2410\nTP: 2380\n"
    r = _go(text)
    blocks = r.blocks
    assert blocks is not None and len(blocks) == 2
    # direction without numbers -> PARTIAL; numbers without direction stay
    # non-executable. No block may borrow the other's missing slot.
    assert blocks[0].outcome is ParseResultState.PARTIAL
    assert blocks[1].outcome is ParseResultState.NO_SIGNAL
    assert _parsed_indices(r) == []
    assert r.outcome is ParseResultState.PARTIAL
    assert _fragment(blocks[0], CandidateSlot.DIRECTION) is not None
    # the direction block's entry stays UNRESOLVED — it never borrows the
    # numbers from the other block (anti-merge, ADR 0013 §4)
    entry0 = _fragment(blocks[0], CandidateSlot.ENTRY)
    assert entry0 is not None and entry0.value is None
    assert entry0.state is FragmentState.UNRESOLVED
    assert _fragment(blocks[1], CandidateSlot.DIRECTION) is None
    # the number block keeps its numbers unbound to any executable signal
    entry1 = _fragment(blocks[1], CandidateSlot.ENTRY)
    assert entry1 is None or entry1.value is not None


# ---------------------------------------------------------------------------
# 9. source-span correctness
# ---------------------------------------------------------------------------


def test_source_spans_exact_and_disjoint() -> None:
    raw = make_raw(M19_STYLE_4)
    runtime = make_mb_runtime()
    r = parse(raw, make_metadata(PROVIDER), runtime)
    blocks = r.blocks
    assert blocks is not None
    normalized = normalize(raw.raw_text, runtime)
    positioned, _ = tokenize(normalized, runtime)
    for i, b in enumerate(blocks):
        blk = b.block
        assert blk.index == i
        assert blk.separator_kind is not None
        assert (blk.raw_start, blk.raw_end) == normalized.source_map.raw_span_for(
            blk.norm_start, blk.norm_end
        )
        slice_text = raw.raw_text[blk.raw_start : blk.raw_end]
        assert slice_text.strip() != ""
        assert "⸻" not in slice_text
        # every non-boundary token inside the block's normalized bounds
        # projects into the block's raw interval
        for s, e, _tok in positioned:
            if blk.norm_start <= s and e <= blk.norm_end:
                rs, re_ = normalized.source_map.raw_span_for(s, e)
                assert blk.raw_start <= rs and re_ <= blk.raw_end
    # strictly increasing, non-overlapping block spans
    for prev, nxt in itertools.pairwise(blocks):
        assert nxt.block.raw_start > prev.block.raw_end
        assert nxt.block.norm_start > prev.block.norm_end


# ---------------------------------------------------------------------------
# 10. deterministic repeated parsing
# ---------------------------------------------------------------------------


def test_deterministic_repeated_parsing() -> None:
    r1 = _go(M19_CORPUS)
    r2 = _go(M19_CORPUS)
    assert r1 == r2
    r3 = _go(M19_STYLE_4)
    r4 = _go(M19_STYLE_4)
    assert r3 == r4


# ---------------------------------------------------------------------------
# 11. existing profiles 001-017 never segment (regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "provider,text",
    [
        (
            "provider_013",
            "NEW ORDER - XAUUSD Sell 📈\n# 508432522\n\n----------{ NEW }----------\nEntry: 2656.00 [Lots: 2.50]\nSL:    2659.99 [39.9 Pips]\nTP:    2647.79 [82.1 Pips]\nRR:    2.06\n---------------------------\n",
        ),
        (
            "provider_001",
            "XAUUSD - SELL LIMIT\n@ 2429-2432\nSL 2437\nTP1 2421\nTP2 2415",
        ),
        ("provider_014", "XAUUSD BUY NOW\nENTRY: 2650\nSL: 2655\nTP1: 2640\nTP2: 2630"),
    ],
)
def test_existing_profiles_never_segment(provider: str, text: str) -> None:
    from tests.parser._helpers import make_runtime

    r = parse(make_raw(text), make_metadata(provider), make_runtime(provider))
    assert r.blocks is None
