"""Phase 2F adversarial audit of the multi-block engine (ADR 0013).

Locks in the adversarial properties verified during the audit:

- cross-block isolation: BUY/price, instrument/SL, direction/TP and
  close-wording captures MUST stay block-local (no silent merging);
- global source-span invariants: block spans, fragment/candidate/
  conflict spans, token partition and SourceMap projections never cross
  a block boundary; re-parsing is byte-identical (determinism);
- segmentation edge cases: divider-like text that is NOT a declared
  separator, inline/trailing/leading dividers, empty sections, DELETE
  events and structural overflow;
- load-time rejection of normalization-rewritten (inert) dividers;
- linear scaling under pathological section counts (no O(B*T) passes).
"""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    MessageEvent,
    ParseResultState,
)
from packages.parser.pipeline import normalize, tokenize
from packages.parser.profiles import ProfileLoadError, load_profile
from packages.parser.safety import MAX_DIGIT_RUN
from packages.parser_profiles.data.common import COMMON_RULE_SET
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw
from tests.parser.blocks._profile import MULTIBLOCK_PROFILE, make_mb_runtime

PROVIDER = "test_multiblock"


def _go(text: str, event: MessageEvent = MessageEvent.CREATE):
    return parse(make_raw(text), make_metadata(PROVIDER, event), make_mb_runtime())


def _fragment(block, slot):
    return next((f for f in block.ir.fragments if f.slot is slot), None)


def _assert_spans_block_local(result) -> None:
    """Every evidence/candidate/conflict/ambiguity span lies inside its
    block's raw span; consecutive blocks are disjoint."""
    assert result.blocks is not None
    for prev, curr in zip(result.blocks, result.blocks[1:]):
        assert prev.block.norm_end <= curr.block.norm_start
        assert prev.block.raw_end <= curr.block.raw_start
    for bp in result.blocks:
        blk_start, blk_end = bp.block.raw_start, bp.block.raw_end

        def in_block(span, blk_start=blk_start, blk_end=blk_end) -> None:
            assert blk_start <= span.start and span.end <= blk_end

        for f in bp.ir.fragments:
            for ev in f.evidence:
                if ev.span is not None:
                    in_block(ev.span)
        for c in bp.ir.candidates:
            in_block(c.source_span)
            for ev in c.provenance:
                if ev.span is not None:
                    in_block(ev.span)
        for conflict in bp.ir.conflicts:
            for span in conflict.spans:
                in_block(span)
        for amb in bp.ir.ambiguities:
            for span in amb.spans:
                in_block(span)
            for cand in amb.candidates:
                in_block(cand.source_span)


def _assert_token_partition(text: str, result) -> None:
    """Every non-whitespace, non-divider token belongs to exactly one
    block; block raw bounds equal the SourceMap projection."""
    from packages.parser.pipeline import _find_divider_spans

    nm = normalize(make_raw(text).raw_text, make_mb_runtime())
    positioned, _ = tokenize(nm, make_mb_runtime())
    smap = nm.source_map
    assert result.blocks is not None
    blocks = [bp.block for bp in result.blocks]
    for blk in blocks:
        assert smap.raw_span_for(blk.norm_start, blk.norm_end) == (
            blk.raw_start,
            blk.raw_end,
        )
    divider_spans = _find_divider_spans(
        nm.normalized_text, tuple(make_mb_runtime().profile.section_dividers)
    )
    for start, end, _tok in positioned:
        if end - start == 1 and nm.normalized_text[start:end].isspace():
            continue
        if any(d0 <= start and end <= d1 for d0, d1 in divider_spans):
            continue
        owners = [b for b in blocks if b.norm_start <= start and end <= b.norm_end]
        assert len(owners) == 1
        raw_start, raw_end = smap.char_ranges[start]
        assert owners[0].raw_start <= raw_start and raw_end <= owners[0].raw_end


def _assert_deterministic(text: str, first) -> None:
    assert _go(text) == first


# ---------------------------------------------------------------------------
# cross-block capture security
# ---------------------------------------------------------------------------


def test_buy_block_cannot_capture_price_from_next_block() -> None:
    r = _go("BUY XAUUSD\n⸻\n2400\n")
    assert r.outcome is ParseResultState.PARTIAL
    b0, _b1 = r.blocks
    entry = _fragment(b0, CandidateSlot.ENTRY)
    assert entry is None or entry.value is None
    assert all(f.value is None or "2400" not in str(f.value) for f in b0.ir.fragments)


def test_instrument_block_cannot_capture_sl_from_next_block() -> None:
    r = _go("BUY EURUSD\n⸻\nSL: 2410\n")
    b0, b1 = r.blocks
    assert _fragment(b0, CandidateSlot.SL) is None
    assert _fragment(b1, CandidateSlot.SL) is not None


def test_direction_block_cannot_capture_tp_from_next_block() -> None:
    r = _go("SELL XAUUSD\n⸻\nTP: 2380\n")
    b0, b1 = r.blocks
    assert _fragment(b0, CandidateSlot.TP) is None
    assert _fragment(b1, CandidateSlot.TP) is not None


def test_close_wording_in_one_block_does_not_suppress_the_other() -> None:
    # close wording is an exclusion constraint; constraints are block-scoped
    r = _go(
        "Should close half now, maybe\n⸻\nBUY XAUUSD Entry: 2400 SL: 2410 TP: 2380\n"
    )
    b0, b1 = r.blocks
    assert b0.outcome is ParseResultState.PARSED
    assert b1.outcome is ParseResultState.PARSED
    assert all(
        f.value is None
        for f in b0.ir.fragments
        if f.slot in (CandidateSlot.ENTRY, CandidateSlot.SL, CandidateSlot.TP)
    )
    assert _fragment(b1, CandidateSlot.INSTRUMENT) is not None
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    _assert_spans_block_local(r)


def test_opposite_directions_in_adjacent_blocks_never_conflict() -> None:
    r = _go(
        "SELL XAUUSD Entry: 2400 SL: 2410 TP: 2380\n⸻\nBUY XAUUSD Entry: 2401 SL: 2390 TP: 2420\n"
    )
    b0, b1 = r.blocks
    assert b0.outcome is ParseResultState.PARSED
    assert b1.outcome is ParseResultState.PARSED
    assert b0.ir.conflicts == () and b1.ir.conflicts == ()
    assert r.ir.conflicts == ()
    assert _fragment(b0, CandidateSlot.DIRECTION).value.name == "SELL"
    assert _fragment(b1, CandidateSlot.DIRECTION).value.name == "BUY"


def test_distinct_instruments_stay_in_their_own_blocks() -> None:
    r = _go("BUY XAUUSD Entry: 2400\n⸻\nBUY EURUSD Entry: 1.10\n")
    b0, b1 = r.blocks
    inst0 = _fragment(b0, CandidateSlot.INSTRUMENT)
    inst1 = _fragment(b1, CandidateSlot.INSTRUMENT)
    assert inst0 is not None and inst1 is not None
    assert str(inst0.value) != str(inst1.value)
    _assert_spans_block_local(r)


def test_action_block_mentioning_nothing_cannot_steal_signal_payload() -> None:
    r = _go(
        "Close all positions now please\n⸻\nBUY XAUUSD Entry: 2400 SL: 2410 TP: 2380\n"
    )
    b0, b1 = r.blocks
    assert b1.outcome is ParseResultState.PARSED
    assert _fragment(b1, CandidateSlot.INSTRUMENT) is not None
    assert r.ir.fragments == () or _fragment(b0, CandidateSlot.ENTRY) is None
    _assert_spans_block_local(r)


# ---------------------------------------------------------------------------
# duplicate-block handling
# ---------------------------------------------------------------------------


def test_duplicate_feed_block_marked_but_never_collapsed() -> None:
    text = (
        "BUY XAUUSD Entry: 2400 SL: 2410\n⸻\n"
        "BUY  XAUUSD  Entry:  2400  SL:  2410\n⸻\n"
        "SELL XAUUSD Entry: 2400 SL: 2410\n"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    b0, b1, b2 = r.blocks
    assert b1.duplicate_of == 0
    assert b0.duplicate_of is None
    assert b2.duplicate_of is None  # opposite direction is NOT a duplicate

    # duplicates keep full independent IRs (no semantic collapse)
    def shape(bp):
        return [(f.slot.name, str(f.value), f.state.name) for f in bp.ir.fragments]

    assert shape(b1) == shape(b0) and shape(b1) != []
    # duplicate blocks still carry distinct raw offsets
    assert (b0.block.raw_start, b0.block.raw_end) != (
        b1.block.raw_start,
        b1.block.raw_end,
    )
    _assert_spans_block_local(r)
    _assert_token_partition(text, r)
    _assert_deterministic(text, r)


# ---------------------------------------------------------------------------
# segmentation edge cases
# ---------------------------------------------------------------------------


def test_divider_like_text_that_is_not_declared_never_segments() -> None:
    for text in (
        "BUY XAUUSD Entry: 2400\n----------{ NEW }----------\nSELL EURUSD Entry: 1.10\n",
        "BUY XAUUSD Entry: 2400\n---\nSL: 2410\n",
        "BUY XAUUSD Entry: 2400\n_______\nSL: 2410\n",
    ):
        r = _go(text)
        assert r.blocks is None, text


def test_adjacent_declared_divider_glyphs_form_separate_boundaries() -> None:
    r = _go("BUY XAUUSD Entry: 2400\n⸻⸻\nSL: 2410\n")
    assert r.blocks is not None and len(r.blocks) == 2


def test_inline_divider_splits_with_no_blank_line() -> None:
    text = "BUY XAUUSD Entry: 2400\n⸻SELL EURUSD Entry: 1.10\n"
    r = _go(text)
    assert r.blocks is not None and len(r.blocks) == 2
    raw = make_raw(text).raw_text
    for bp in r.blocks:
        assert "⸻" not in raw[bp.block.raw_start : bp.block.raw_end]
    _assert_spans_block_local(r)
    _assert_token_partition(text, r)
    _assert_deterministic(text, r)


def test_trailing_and_leading_separators_drop_empty_sections() -> None:
    r = _go("BUY XAUUSD Entry: 2400\n⸻\nSELL EURUSD Entry: 1.10\n⸻\n⸻\n")
    assert r.blocks is not None and len(r.blocks) == 2
    r = _go("⸻\n⸻\nBUY XAUUSD Entry: 2400\n⸻\nSELL EURUSD Entry: 1.10\n")
    assert r.blocks is not None and len(r.blocks) == 2
    assert r.blocks[0].block.index == 0
    _assert_spans_block_local(r)


def test_empty_sections_between_content_are_dropped() -> None:
    r = _go("BUY XAUUSD Entry: 2400\n⸻\n\n⸻\n\n⸻\nSELL EURUSD Entry: 1.10\n")
    assert r.blocks is not None and len(r.blocks) == 2
    for bp in r.blocks:
        assert _fragment(bp, CandidateSlot.ENTRY) is not None


def test_all_empty_message_with_dividers_is_single_unit() -> None:
    assert _go("\n⸻\n\n⸻\n\n").blocks is None
    assert _go("⸻").blocks is None


def test_single_content_block_with_divider_declared_is_legacy() -> None:
    r = _go("⸻\nBUY XAUUSD Entry: 2400 SL: 2410 TP: 2380\n")
    assert r.blocks is None
    assert r.outcome is ParseResultState.PARSED


def test_blank_lines_split_only_in_sectioned_messages() -> None:
    # legacy: blank lines inside one signal never split
    legacy = "BUY XAUUSD\nEntry: 2400\n\nSL: 2410\n\nTP: 2380\n"
    r = _go(legacy)
    assert r.blocks is None
    # sectioned: blank-line runs ARE weak boundaries (ADR 0013 audit) and
    # fields stay block-local (no cross-block merge into one signal)
    text = legacy + "⸻\nnote text here\n"
    r = _go(text)
    assert r.blocks is not None and len(r.blocks) == 4
    assert _fragment(r.blocks[0], CandidateSlot.SL) is None
    assert _fragment(r.blocks[0], CandidateSlot.TP) is None
    assert _fragment(r.blocks[1], CandidateSlot.SL) is not None
    assert _fragment(r.blocks[2], CandidateSlot.TP) is not None
    assert all(f.slot is not CandidateSlot.SL for f in r.ir.fragments)
    _assert_spans_block_local(r)
    _assert_token_partition(text, r)
    _assert_deterministic(text, r)


def test_delete_event_never_segments() -> None:
    r = _go(
        "BUY XAUUSD Entry: 2400\n⸻\nSELL EURUSD Entry: 1.10\n",
        event=MessageEvent.DELETE,
    )
    assert r.blocks is None


def test_structural_overflow_rejects_whole_sectioned_message() -> None:
    overflow = "9" * (MAX_DIGIT_RUN + 5)
    r = _go("BUY XAUUSD Entry: 2400\n⸻\nXAUUSD Entry: " + overflow + "\n")
    assert r.outcome is ParseResultState.MALFORMED
    assert r.blocks is None


# ---------------------------------------------------------------------------
# source-span + determinism evidence on the corpus-shaped messages
# ---------------------------------------------------------------------------


def test_m19_style_duplicate_feeds_isolation_and_determinism() -> None:
    text = (
        "Cronos Markets data:\nSELL STOP\nEntry: 53071\nSL: 53241\nTP: 52995\n\n"
        "BUY STOP\nEntry: 53238\nSL: 53068\nTP: 53314\n⸻\n"
        "Funding Dynasty data:\nSELL STOP\nEntry: 53071\nSL: 53241\nTP: 52995\n\n"
        "BUY STOP\nEntry: 53238\nSL: 53068\nTP: 53314\n"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    assert [bp.outcome for bp in r.blocks] == [ParseResultState.PARSED] * 4
    assert r.blocks[2].duplicate_of == 0 and r.blocks[3].duplicate_of == 1
    _assert_spans_block_local(r)
    _assert_token_partition(text, r)
    _assert_deterministic(text, r)


def test_promoted_single_parsed_block_ir_is_block_local() -> None:
    text = (
        "Market report: gold steady.\n\nWeekly outlook unchanged.\n⸻\n"
        "BUY XAUUSD Entry: 2400 SL: 2410 TP: 2380\n"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.PARSED
    assert r.blocks is not None and len(r.blocks) == 3
    assert r.ir == r.blocks[2].ir
    assert _fragment(r.blocks[2], CandidateSlot.ENTRY).value == Price(Decimal(2400))
    assert _fragment(r.blocks[0], CandidateSlot.ENTRY) is None
    _assert_spans_block_local(r)
    _assert_token_partition(text, r)
    _assert_deterministic(text, r)


def test_mixed_event_action_signal_message_isolation() -> None:
    text = (
        "The sell stop order was triggered.\n\nDelete the buy stop order.\n\n⸻\n"
        "Cronos Markets data:\nBUY STOP Order\nEntry: 53241\nSL: 53071\nTP: 53273\n⸻\n"
        "Funding Dynasty data:\nBUY STOP Order\nEntry: 53241\nSL: 53071\nTP: 53273\n"
    )
    r = _go(text)
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    assert [bp.outcome.name for bp in r.blocks] == [
        "PARTIAL",
        "PARTIAL",
        "PARSED",
        "PARSED",
    ]
    assert r.blocks[3].duplicate_of == 2
    _assert_spans_block_local(r)
    _assert_token_partition(text, r)
    _assert_deterministic(text, r)


# ---------------------------------------------------------------------------
# load-time divider validation (inert dividers are fail-open config errors)
# ---------------------------------------------------------------------------


def _load_with_divider(divider: str):
    profile = dict(
        MULTIBLOCK_PROFILE, provider_name="divcheck", section_dividers=[divider]
    )
    return load_profile(profile, {"common": COMMON_RULE_SET})


@pytest.mark.parametrize(
    "divider",
    ["⸻", "----", "=====", "NEW ⸻"],
)
def test_matchable_dividers_load(divider: str) -> None:
    runtime = _load_with_divider(divider)
    assert runtime.profile.section_dividers == (divider,)


@pytest.mark.parametrize(
    "divider",
    [
        "*NEW*",  # markdown chars are stripped by normalization
        "NEW  ⸻",  # whitespace runs collapse to one space
        "NEW\n⸻",  # newline collapses to a space
        "––",  # unicode dashes are canonicalized to the separator
    ],
)
def test_inert_dividers_are_rejected_at_load(divider: str) -> None:
    with pytest.raises(ProfileLoadError) as exc_info:
        _load_with_divider(divider)
    assert exc_info.value.code == "invalid_profile_data"


def test_zero_width_prefixed_divider_is_rejected() -> None:
    with pytest.raises(ProfileLoadError) as exc_info:
        _load_with_divider("\u200b⸻")
    assert exc_info.value.code == "invalid_profile_data"


# ---------------------------------------------------------------------------
# pathological sizes (linear scaling; input bounded by max_message_length)
# ---------------------------------------------------------------------------


def test_many_sections_remain_fast_and_deterministic() -> None:
    text = "x\n⸻\n" * 1599 + "x"
    t0 = time.perf_counter()
    r = _go(text)
    elapsed = time.perf_counter() - t0
    assert r.blocks is not None and len(r.blocks) == 1600
    assert r.outcome is ParseResultState.NO_SIGNAL
    # generous guard against an O(B*T) regression (was >1.3s quadratic;
    # linear implementation is well under 1s on constrained hardware)
    assert elapsed < 2.0, f"segmentation regressed: {elapsed:.3f}s"
    _assert_deterministic(text, r)


def test_long_separator_run_stays_single_content() -> None:
    r = _go(
        "BUY XAUUSD Entry: 2400 SL: 2410 TP: 2380\n"
        + "⸻" * 700
        + "\nSELL EURUSD Entry: 1.10\n"
    )
    assert r.outcome is ParseResultState.MULTI_SIGNAL
    assert r.blocks is not None and len(r.blocks) == 2
    _assert_spans_block_local(r)
