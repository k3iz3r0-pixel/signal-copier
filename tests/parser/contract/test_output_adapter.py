"""OUTPUT ADAPTER contract tests (design §25 step 5).

Authoritative contracts under test:

- design §4.1/§4.4/§4.6: the adapter converts CanonicalParserIR into exactly
  one explicit result (Signal | SignalInstruction | non-signal); identity
  UUIDs are caller-supplied; timestamps come from MessageMetadata.
- ADR 0004: the adapter is the only IR -> Signal/SignalInstruction converter.
- ADR 0005: a missing trigger resolves to UNSPECIFIED and is never promoted
  to MARKET.
- ADR 0006: PARTIAL / follow-up-only results cannot become Signals here.
- ADR 0009: actions become SignalInstructions with a lossless payload.
- ADR 0013 §5: MULTI_SIGNAL aggregates are refused (anti-merge rule).
- Financial safety: representational conflicts (MARKET geometry with a
  preserved entry price; range stop-loss) are surfaced as explicit
  NON_SIGNAL reasons, never silently dropped or re-labeled; Signal semantic
  invariants propagate unchanged.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from packages.parser import (
    AdapterOutput,
    AdapterOutputKind,
    CandidateSlot,
    CanonicalParserIR,
    Condition,
    ConditionKind,
    CorrelationRequest,
    CorrelationRequestKind,
    FragmentState,
    ParsedFragment,
    ParseResult,
    ParseResultState,
    adapt_parse_result,
    parse,
)
from packages.signal_core.domain import (
    Signal,
    SignalIdentity,
    SignalInstruction,
)
from packages.signal_core.enums import (
    AssetClass,
    EntryGeometry,
    EntryTrigger,
    InstructionType,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.value_objects import (
    Instrument,
    Price,
    PriceRange,
    ProviderSource,
)
from tests.parser._helpers import make_metadata, make_raw, make_runtime

IDENTITY = SignalIdentity(
    logical_signal_id=UUID("00000000-0000-0000-0000-000000000001"),
    provider_identity=ProviderSource(
        provider_name="provider_001", signal_reference="ref-1"
    ),
)

INSTRUMENTS = {
    "EURUSD": Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
    "XAUUSD": Instrument(canonical_symbol="XAUUSD", asset_class=AssetClass.COMMODITY),
}


def _frag(slot: CandidateSlot, value: object) -> ParsedFragment:
    return ParsedFragment(slot=slot, value=value, state=FragmentState.RESOLVED)


def _ir(
    fragments: tuple[ParsedFragment, ...] = (),
    conditions: tuple[Condition, ...] = (),
    correlation_request: CorrelationRequest | None = None,
) -> CanonicalParserIR:
    return CanonicalParserIR(
        candidates=(),
        unresolved_fields=(),
        fragments=fragments,
        conflicts=(),
        ambiguities=(),
        evidence=(),
        normalization_decisions=(),
        conditions=conditions,
        provider_id="provider_001",
        parser_version="test",
        correlation_request=correlation_request,
    )


def _result(
    outcome: ParseResultState, ir: CanonicalParserIR | None = None
) -> ParseResult:
    return ParseResult(outcome=outcome, ir=ir if ir is not None else _ir())


def _full_limit_fragments() -> tuple[ParsedFragment, ...]:
    return (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(CandidateSlot.ENTRY, Price(Decimal("1.1000"))),
        _frag(CandidateSlot.ENTRY_TRIGGER, EntryTrigger.LIMIT),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.SINGLE),
        _frag(CandidateSlot.SL, Price(Decimal("1.0950"))),
        _frag(CandidateSlot.TP, (Price(Decimal("1.1100")),)),
    )


# ---------------------------------------------------------------------------
# PARSED -> Signal
# ---------------------------------------------------------------------------


def test_parsed_full_limit_signal_maps_to_signal() -> None:
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(_full_limit_fragments())),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.SIGNAL
    assert output.instruction is None and output.reason is None
    signal = output.signal
    assert isinstance(signal, Signal)
    assert signal.identity is IDENTITY
    assert signal.instrument is INSTRUMENTS["EURUSD"]
    assert signal.direction is TradeDirection.BUY
    assert signal.entry_geometry is EntryGeometry.SINGLE
    assert signal.entry_trigger is EntryTrigger.LIMIT
    assert signal.created_at_utc == datetime(2025, 1, 1, tzinfo=UTC)
    assert signal.entry_price == Price(Decimal("1.1000"))
    assert signal.entry_range is None
    assert signal.entry_levels == ()
    assert signal.stop_loss == Price(Decimal("1.0950"))
    assert signal.take_profit_targets == (Price(Decimal("1.1100")),)
    assert signal.status is SignalStatus.COMPLETE
    assert signal.lifecycle_state is LifecycleState.ACTIVE


def test_parsed_market_without_entry_maps_to_signal() -> None:
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.SELL),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(CandidateSlot.ENTRY_TRIGGER, EntryTrigger.MARKET),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.MARKET),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.SIGNAL
    assert output.signal is not None
    assert output.signal.entry_price is None
    assert output.signal.entry_geometry is EntryGeometry.MARKET
    assert output.signal.entry_trigger is EntryTrigger.MARKET


def test_missing_trigger_defaults_to_unspecified_never_market() -> None:
    """ADR 0005 / design §4.3: absent trigger must never be promoted to MARKET."""
    fragments = tuple(
        f for f in _full_limit_fragments() if f.slot is not CandidateSlot.ENTRY_TRIGGER
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.signal is not None
    assert output.signal.entry_trigger is EntryTrigger.UNSPECIFIED


def test_range_entry_maps_to_entry_range() -> None:
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(
            CandidateSlot.ENTRY,
            PriceRange(Price(Decimal("1.1000")), Price(Decimal("1.1010"))),
        ),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.RANGE),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.signal is not None
    assert output.signal.entry_range == PriceRange(
        Price(Decimal("1.1000")), Price(Decimal("1.1010"))
    )
    assert output.signal.entry_price is None


def test_multiple_entries_map_to_entry_levels() -> None:
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(
            CandidateSlot.ENTRY,
            (Price(Decimal("1.1000")), Price(Decimal("1.1010"))),
        ),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.MULTIPLE),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.signal is not None
    assert output.signal.entry_levels == (
        Price(Decimal("1.1000")),
        Price(Decimal("1.1010")),
    )
    assert output.signal.entry_price is None


# ---------------------------------------------------------------------------
# Representational conflicts are surfaced, never silently resolved
# ---------------------------------------------------------------------------


def test_market_geometry_with_preserved_entry_is_explicit_non_signal() -> None:
    """Real corpus M24 (provider_014): MARKET trigger + preserved entry price.

    The Phase 1 Signal invariant forbids entry_price under MARKET geometry.
    The adapter must refuse explicitly — never drop the price, never
    re-label the geometry.
    """
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.SELL),
        _frag(CandidateSlot.INSTRUMENT, "XAUUSD"),
        _frag(CandidateSlot.ENTRY, Price(Decimal("4133.00"))),
        _frag(CandidateSlot.ENTRY_TRIGGER, EntryTrigger.MARKET),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.MARKET),
        _frag(CandidateSlot.SL, Price(Decimal("4152.00"))),
        _frag(CandidateSlot.TP, (Price(Decimal("4076.00")),)),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_014"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.signal is None
    assert output.reason == "market_geometry_with_entry_not_representable"


def test_stop_loss_range_is_not_representable() -> None:
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(CandidateSlot.ENTRY, Price(Decimal("1.1000"))),
        _frag(CandidateSlot.ENTRY_TRIGGER, EntryTrigger.LIMIT),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.SINGLE),
        _frag(
            CandidateSlot.SL,
            PriceRange(Price(Decimal("1.0940")), Price(Decimal("1.0960"))),
        ),
        _frag(CandidateSlot.TP, (Price(Decimal("1.1100")),)),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == "stop_loss_range_not_representable"


def test_mixed_entry_tuple_is_not_representable() -> None:
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(
            CandidateSlot.ENTRY,
            (Price(Decimal("1.1000")), PriceRange(Price(Decimal("1.2")), None)),
        ),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.MULTIPLE),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == "entry_levels_shape_not_representable"


def test_signal_invariant_violations_propagate() -> None:
    """BUY with SL above entry: the Phase 1 domain model is the enforcement
    point; the adapter must not absorb semantic invariant violations."""
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
        _frag(CandidateSlot.ENTRY, Price(Decimal("1.1000"))),
        _frag(CandidateSlot.ENTRY_TRIGGER, EntryTrigger.LIMIT),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.SINGLE),
        _frag(CandidateSlot.SL, Price(Decimal("1.2000"))),
    )
    with pytest.raises(ValueError, match="stop_loss"):
        adapt_parse_result(
            _result(ParseResultState.PARSED, _ir(fragments)),
            metadata=make_metadata("provider_001"),
            identity=IDENTITY,
            instruments=INSTRUMENTS,
        )


# ---------------------------------------------------------------------------
# Missing canonical fields are explicit NON_SIGNALs, never guesses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("drop_slot", "expected_reason"),
    [
        (CandidateSlot.DIRECTION, "direction_fragment_missing"),
        (CandidateSlot.INSTRUMENT, "instrument_fragment_missing"),
        (CandidateSlot.ENTRY_GEOMETRY, "entry_geometry_fragment_missing"),
    ],
)
def test_missing_required_fragment_is_explicit_non_signal(
    drop_slot: CandidateSlot, expected_reason: str
) -> None:
    fragments = tuple(f for f in _full_limit_fragments() if f.slot is not drop_slot)
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == expected_reason
    assert output.signal is None and output.instruction is None


def test_unmapped_symbol_is_never_guessed() -> None:
    """No AssetClass inference: an unmapped symbol must not become a Signal."""
    fragments = (
        _frag(CandidateSlot.DIRECTION, TradeDirection.BUY),
        _frag(CandidateSlot.INSTRUMENT, "EJ"),
        _frag(CandidateSlot.ENTRY, Price(Decimal("100.0"))),
        _frag(CandidateSlot.ENTRY_TRIGGER, EntryTrigger.LIMIT),
        _frag(CandidateSlot.ENTRY_GEOMETRY, EntryGeometry.SINGLE),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments)),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == "instrument_unmapped"


# ---------------------------------------------------------------------------
# PARSED action -> SignalInstruction (lossless payload)
# ---------------------------------------------------------------------------


def test_action_with_number_becomes_instruction_with_lossless_payload() -> None:
    result = parse(
        make_raw("EURUSD SL 3320"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert result.outcome is ParseResultState.PARSED
    output = adapt_parse_result(
        result,
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.INSTRUCTION
    assert output.signal is None and output.reason is None
    instruction = output.instruction
    assert isinstance(instruction, SignalInstruction)
    assert instruction.instruction_type is InstructionType.MOVE_SL
    assert instruction.signal_identity is IDENTITY
    assert instruction.created_at_utc == datetime(2025, 1, 1, tzinfo=UTC)
    payload = dict(instruction.payload)
    assert payload["instrument"] == "EURUSD"
    assert payload["sl"] == Price(Decimal(3320))
    assert "direction" not in payload


def test_action_flags_are_preserved_in_payload() -> None:
    result = parse(
        make_raw("CANCEL PENDING"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert result.outcome is ParseResultState.PARSED
    output = adapt_parse_result(
        result,
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.INSTRUCTION
    assert output.instruction is not None
    assert output.instruction.instruction_type is InstructionType.CANCEL
    payload = dict(output.instruction.payload)
    assert payload["action_flags"] == (("cancel_pending", True),)


def test_correlation_request_is_recorded_in_payload() -> None:
    fragments = (
        _frag(CandidateSlot.ACTION, InstructionType.MOVE_SL),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
    )
    ir = _ir(
        fragments,
        correlation_request=CorrelationRequest(
            kind=CorrelationRequestKind.TARGET_LAST_SIGNAL,
            target=None,
        ),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, ir),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.INSTRUCTION
    assert output.instruction is not None
    payload = dict(output.instruction.payload)
    assert payload["correlation_request"] == "TARGET_LAST_SIGNAL"


def test_conditions_are_recorded_in_payload() -> None:
    fragments = (
        _frag(CandidateSlot.ACTION, InstructionType.MOVE_SL),
        _frag(CandidateSlot.INSTRUMENT, "EURUSD"),
    )
    condition = Condition(
        kind=ConditionKind.AT_PRICE,
        params=(("price", Price(Decimal("1.2000"))),),
    )
    output = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(fragments, (condition,))),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.INSTRUCTION
    assert output.instruction is not None
    payload = dict(output.instruction.payload)
    assert payload["conditions"] == (
        ("AT_PRICE", (("price", Price(Decimal("1.2000"))),)),
    )


# ---------------------------------------------------------------------------
# Non-PARSED outcomes are explicit NON_SIGNALs (ADR 0005/0006/0013)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "expected_reason"),
    [
        (ParseResultState.PARTIAL, "partial_awaiting_correlation"),
        (ParseResultState.AMBIGUOUS, "ambiguous_requires_human_or_correlation"),
        (ParseResultState.MALFORMED, "malformed"),
        (ParseResultState.UNSUPPORTED, "unsupported_feature"),
        (ParseResultState.NO_SIGNAL, "no_signal"),
        (
            ParseResultState.MULTI_SIGNAL,
            "multi_signal_blocks_require_individual_conversion",
        ),
    ],
)
def test_every_non_parsed_outcome_is_explicit_non_signal(
    outcome: ParseResultState, expected_reason: str
) -> None:
    output = adapt_parse_result(
        _result(outcome),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == expected_reason
    assert output.signal is None
    assert output.instruction is None


# ---------------------------------------------------------------------------
# AdapterOutput shape, immutability, determinism, argument validation
# ---------------------------------------------------------------------------


def test_adapter_output_shape_invariants() -> None:
    with pytest.raises(ValueError):
        AdapterOutput(kind=AdapterOutputKind.NON_SIGNAL)
    with pytest.raises(TypeError):
        AdapterOutput(kind=AdapterOutputKind.SIGNAL)
    with pytest.raises(ValueError):
        AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason="x",
            signal=Signal(
                identity=IDENTITY,
                instrument=INSTRUMENTS["EURUSD"],
                direction=TradeDirection.BUY,
                entry_geometry=EntryGeometry.MARKET,
                entry_trigger=EntryTrigger.MARKET,
                created_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
            ),
        )


def test_adapter_output_is_frozen() -> None:
    output = adapt_parse_result(
        _result(ParseResultState.NO_SIGNAL),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
    )
    with pytest.raises(FrozenInstanceError):
        output.reason = "mutated"  # type: ignore[misc]


def test_adapt_is_deterministic() -> None:
    first = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(_full_limit_fragments())),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    second = adapt_parse_result(
        _result(ParseResultState.PARSED, _ir(_full_limit_fragments())),
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert first == second


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"metadata": make_metadata("provider_001"), "identity": IDENTITY}, "result"),
        (
            {
                "result": "x",
                "metadata": make_metadata("provider_001"),
                "identity": IDENTITY,
            },
            "result",
        ),
        (
            {
                "result": ParseResult(outcome=ParseResultState.NO_SIGNAL, ir=_ir()),
                "metadata": "x",
                "identity": IDENTITY,
            },
            "metadata",
        ),
        (
            {
                "result": ParseResult(outcome=ParseResultState.NO_SIGNAL, ir=_ir()),
                "metadata": make_metadata("provider_001"),
                "identity": "x",
            },
            "identity",
        ),
        (
            {
                "result": ParseResult(outcome=ParseResultState.NO_SIGNAL, ir=_ir()),
                "metadata": make_metadata("provider_001"),
                "identity": IDENTITY,
                "instruments": {"EURUSD": "not-an-instrument"},
            },
            "instruments",
        ),
        (
            {
                "result": ParseResult(outcome=ParseResultState.NO_SIGNAL, ir=_ir()),
                "metadata": make_metadata("provider_001"),
                "identity": IDENTITY,
                "instruments": {1: INSTRUMENTS["EURUSD"]},
            },
            "instruments",
        ),
    ],
)
def test_argument_type_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(TypeError, match=match):
        adapt_parse_result(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Real-engine integration
# ---------------------------------------------------------------------------


def test_real_engine_limit_signal_end_to_end() -> None:
    result = parse(
        make_raw("BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert result.outcome is ParseResultState.PARSED
    output = adapt_parse_result(
        result,
        metadata=make_metadata("provider_001"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.SIGNAL
    assert output.signal is not None
    assert output.signal.direction is TradeDirection.BUY
    assert output.signal.entry_trigger is EntryTrigger.LIMIT
    assert output.signal.entry_price == Price(Decimal("1.1000"))
    assert output.signal.stop_loss == Price(Decimal("1.0950"))
    assert output.signal.take_profit_targets == (Price(Decimal("1.1100")),)


def test_real_engine_m24_market_with_entry_surfaces_conflict() -> None:
    from tests.fixtures.providers.provider_014.canonical import EXAMPLES

    raw_text = next(
        e["raw_text"] for e in EXAMPLES if e["name"] == "m24_sell_now_market"
    )
    result = parse(
        make_raw(str(raw_text)),
        make_metadata("provider_014"),
        make_runtime("provider_014"),
    )
    assert result.outcome is ParseResultState.PARSED
    output = adapt_parse_result(
        result,
        metadata=make_metadata("provider_014"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == "market_geometry_with_entry_not_representable"
    # The conflict is fully auditable: the ParseResult still carries the
    # preserved entry; the adapter dropped nothing.
    entry = [f for f in result.ir.fragments if f.slot is CandidateSlot.ENTRY]
    assert entry and entry[0].value == Price(Decimal("4133.00"))


def test_real_engine_multi_signal_aggregate_is_refused() -> None:
    from tests.parser.blocks._profile import make_mb_runtime

    text = (
        "⸻\nXAUUSD\nSELL\nEntry: 2400\nSL: 2410\nTP: 2380\n⸻\n"
        "EURUSD\nBUY\nEntry: 1.1000\nSL: 1.1050\nTP: 1.0950\n⸻\n"
    )
    result = parse(make_raw(text), make_metadata("test_multiblock"), make_mb_runtime())
    assert result.outcome is ParseResultState.MULTI_SIGNAL
    assert result.blocks is not None and len(result.blocks) == 2
    output = adapt_parse_result(
        result,
        metadata=make_metadata("test_multiblock"),
        identity=IDENTITY,
        instruments=INSTRUMENTS,
    )
    assert output.kind is AdapterOutputKind.NON_SIGNAL
    assert output.reason == "multi_signal_blocks_require_individual_conversion"
