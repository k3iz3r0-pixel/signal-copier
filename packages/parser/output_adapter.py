"""Phase 2 OUTPUT ADAPTER — CanonicalParserIR -> Signal / SignalInstruction / non-signal.

Authoritative sources:

- design §25 step 5 (``packages/parser/output_adapter.py``; IR → Signal /
  SignalInstruction / non-signal) and §4.1/§4.6 (the adapter converts the
  ``CanonicalParserIR`` into one of those three explicit results).
- design §4.4 — all UUIDs needed downstream are produced by the INTEGRATION
  layer, never by the parser; all timestamps come from ``MessageMetadata``.
  This module therefore accepts a caller-supplied ``SignalIdentity`` and
  derives ``created_at_utc`` exclusively from the caller-supplied metadata.
- ADR 0004 — the OUTPUT ADAPTER is the ONLY component that converts
  ``CanonicalParserIR`` into ``Signal`` / ``SignalInstruction`` instances;
  Signal Core receives only resolved canonical semantics.
- ADR 0005 — downstream layers dispatch on ``ParseResult.outcome``; a missing
  numeric entry is resolved to ``EntryTrigger.UNSPECIFIED`` and is NEVER
  promoted to ``MARKET`` (design §4.3 promotion ban).
- ADR 0006 — correlation is Phase 3+. PARTIAL results (multi-message
  construction) and follow-up-only actions cannot become Signals here; they
  are returned as explicit non-signal results carrying the parse outcome.
- ADR 0009 — actions are semantic instructions; the engine resolves the
  canonical ``InstructionType`` (single category table), and this module
  wraps it in a ``SignalInstruction`` whose payload preserves every other
  resolved fragment (no silent loss of signal data).
- ADR 0013 §5 — for ``MULTI_SIGNAL`` the aggregate IR is explicitly EMPTY and
  consumers MUST read ``blocks``; this module refuses the aggregate (the
  anti-merge rule) instead of silently picking one signal.

Representational-conflict policy (financial safety; AGENTS.md §7): when a
resolved parser shape is not representable in the Phase 1 ``Signal`` model —
e.g. MARKET geometry with a preserved entry price (real corpus M24, provider
014) or a range stop-loss — the adapter returns an explicit NON_SIGNAL result
with a stable documented reason. It never drops data silently, never
re-labels engine-derived semantics, and never invents missing financial data
(no ``AssetClass`` inference: symbol → ``Instrument`` resolution is
caller-supplied, per design §23 open question 8). ``Signal`` semantic
invariants (direction/SL/TP ordering) are Phase 1's enforcement point and
propagate unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from packages.parser.enums import (
    CandidateSlot,
    FragmentState,
    ParseResultState,
)
from packages.parser.types import (
    CanonicalParserIR,
    MessageMetadata,
    ParsedFragment,
    ParseResult,
)
from packages.signal_core.domain import (
    Signal,
    SignalIdentity,
    SignalInstruction,
)
from packages.signal_core.enums import (
    EntryGeometry,
    EntryTrigger,
    InstructionType,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.value_objects import Instrument, Price, PriceRange

__all__ = [
    "AdapterOutput",
    "AdapterOutputKind",
    "adapt_parse_result",
]


# Stable NON_SIGNAL reason codes (documented public surface). Never
# localized, never renamed without an ADR: callers dispatch on them.
REASON_PARTIAL_AWAITING_CORRELATION = "partial_awaiting_correlation"
REASON_AMBIGUOUS_REQUIRES_HUMAN_OR_CORRELATION = (
    "ambiguous_requires_human_or_correlation"
)
REASON_MALFORMED = "malformed"
REASON_UNSUPPORTED_FEATURE = "unsupported_feature"
REASON_NO_SIGNAL = "no_signal"
REASON_MULTI_SIGNAL_BLOCKS_REQUIRE_INDIVIDUAL_CONVERSION = (
    "multi_signal_blocks_require_individual_conversion"
)
REASON_DIRECTION_FRAGMENT_MISSING = "direction_fragment_missing"
REASON_INSTRUMENT_FRAGMENT_MISSING = "instrument_fragment_missing"
REASON_INSTRUMENT_UNMAPPED = "instrument_unmapped"
REASON_ENTRY_GEOMETRY_FRAGMENT_MISSING = "entry_geometry_fragment_missing"
REASON_MARKET_GEOMETRY_WITH_ENTRY_NOT_REPRESENTABLE = (
    "market_geometry_with_entry_not_representable"
)
REASON_STOP_LOSS_RANGE_NOT_REPRESENTABLE = "stop_loss_range_not_representable"
REASON_ENTRY_VALUE_INVALID = "entry_value_invalid"
REASON_ENTRY_LEVELS_SHAPE_NOT_REPRESENTABLE = "entry_levels_shape_not_representable"
REASON_TAKE_PROFIT_VALUE_INVALID = "take_profit_value_invalid"
REASON_ENTRY_TRIGGER_VALUE_INVALID = "entry_trigger_value_invalid"
REASON_ACTION_VALUE_INVALID = "action_value_invalid"

_NON_SIGNAL_REASONS: dict[ParseResultState, str] = {
    ParseResultState.PARTIAL: REASON_PARTIAL_AWAITING_CORRELATION,
    ParseResultState.AMBIGUOUS: REASON_AMBIGUOUS_REQUIRES_HUMAN_OR_CORRELATION,
    ParseResultState.MALFORMED: REASON_MALFORMED,
    ParseResultState.UNSUPPORTED: REASON_UNSUPPORTED_FEATURE,
    ParseResultState.NO_SIGNAL: REASON_NO_SIGNAL,
    ParseResultState.MULTI_SIGNAL: (
        REASON_MULTI_SIGNAL_BLOCKS_REQUIRE_INDIVIDUAL_CONVERSION
    ),
}


class AdapterOutputKind(Enum):
    """The three explicit adapter results (design §4.1, §4.6)."""

    SIGNAL = "SIGNAL"
    INSTRUCTION = "INSTRUCTION"
    NON_SIGNAL = "NON_SIGNAL"


@dataclass(frozen=True, slots=True)
class AdapterOutput:
    """Explicit adapter result (exactly one shape per instance).

    ``SIGNAL`` carries ``signal``; ``INSTRUCTION`` carries ``instruction``;
    ``NON_SIGNAL`` carries a stable non-empty ``reason`` code and never a
    Signal/SignalInstruction. The adapter NEVER returns ``None`` and never
    raises for representational mismatches — conflicts are surfaced as
    NON_SIGNAL reasons and remain auditable through the source
    ``ParseResult``/IR.
    """

    kind: AdapterOutputKind
    signal: Signal | None = None
    instruction: SignalInstruction | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AdapterOutputKind):
            raise TypeError("kind must be AdapterOutputKind")
        if self.kind is AdapterOutputKind.SIGNAL:
            if not isinstance(self.signal, Signal):
                raise TypeError("SIGNAL output requires a Signal instance")
            if self.instruction is not None or self.reason is not None:
                raise ValueError(
                    "SIGNAL output must not carry an instruction or a reason"
                )
        elif self.kind is AdapterOutputKind.INSTRUCTION:
            if not isinstance(self.instruction, SignalInstruction):
                raise TypeError(
                    "INSTRUCTION output requires a SignalInstruction instance"
                )
            if self.signal is not None or self.reason is not None:
                raise ValueError(
                    "INSTRUCTION output must not carry a signal or a reason"
                )
        else:
            if not isinstance(self.reason, str) or not self.reason:
                raise ValueError("NON_SIGNAL output requires a non-empty reason code")
            if self.signal is not None or self.instruction is not None:
                raise ValueError(
                    "NON_SIGNAL output must not carry a signal or an instruction"
                )


def _resolved_fragment(
    ir: CanonicalParserIR, slot: CandidateSlot
) -> ParsedFragment | None:
    for fragment in ir.fragments:
        if fragment.slot is slot and fragment.state is FragmentState.RESOLVED:
            return fragment
    return None


def _action_flags(fragment: ParsedFragment) -> tuple[tuple[str, object], ...]:
    """Merged ``action_flags`` evidence entries, in recorded order."""
    entries: list[tuple[str, object]] = []
    for evidence in fragment.evidence:
        if evidence.kind == "action_flags":
            entries.extend((str(key), value) for key, value in evidence.fields)
    return tuple(entries)


def _candidate_winner_values(
    ir: CanonicalParserIR, slot: CandidateSlot
) -> tuple[object, ...]:
    """Resolved winner values for ``slot`` from the IR's candidate tuple.

    ``CanonicalParserIR.candidates`` holds post-resolution winners plus
    PRICE/RANGE reference candidates (design §13.1). Slots other than
    PRICE/RANGE are therefore guaranteed resolved winners. Used only by the
    instruction payload: in action contexts the engine suppresses
    signal-slot FRAGMENTS (e.g. the bare number after CLOSE), but design
    §20.13-§20.15 requires the action operand (``move_sl_to`` /
    ``move_tp_to`` / ``entry_price``) to remain available — it does, as a
    resolved winner in ``candidates``.
    """
    return tuple(
        candidate.value
        for candidate in ir.candidates
        if candidate.slot is slot
        and candidate.slot not in (CandidateSlot.PRICE, CandidateSlot.RANGE)
    )


def _instruction_payload(
    ir: CanonicalParserIR, action_fragment: ParsedFragment
) -> tuple[tuple[str, object], ...]:
    """Lossless instruction payload (design §8, §10.1 layer E).

    Every resolved non-ACTION fragment is preserved under its slot name;
    signal-slot operands suppressed by the engine in action contexts are
    recovered from their resolved winners in ``candidates`` (design
    §20.13-§20.15). Plus action flags, the pending correlation request
    kind, and recorded conditions. Values conform to
    ``ALLOWED_SNAPSHOT_TYPES`` (enforced by ``SignalInstruction``). Fixed
    key order; present-only entries; no duplicate keys.
    """
    payload: list[tuple[str, object]] = []
    present: set[str] = set()

    def _add(key: str, value: object) -> None:
        if key not in present:
            present.add(key)
            payload.append((key, value))

    fragment_map: tuple[tuple[CandidateSlot, str], ...] = (
        (CandidateSlot.INSTRUMENT, "instrument"),
        (CandidateSlot.DIRECTION, "direction"),
        (CandidateSlot.ENTRY, "entry"),
        (CandidateSlot.ENTRY_TRIGGER, "entry_trigger"),
        (CandidateSlot.ENTRY_GEOMETRY, "entry_geometry"),
        (CandidateSlot.SL, "sl"),
        (CandidateSlot.TP, "tp"),
    )
    for slot, key in fragment_map:
        fragment = _resolved_fragment(ir, slot)
        if fragment is not None:
            _add(key, fragment.value)
            continue
        winner_values = _candidate_winner_values(ir, slot)
        if not winner_values:
            continue
        if slot is CandidateSlot.TP:
            _add(key, tuple(winner_values))
        elif len(winner_values) == 1:
            _add(key, winner_values[0])
        else:
            _add(key, tuple(winner_values))
    flags = _action_flags(action_fragment)
    if flags:
        _add("action_flags", flags)
    if ir.correlation_request is not None:
        _add("correlation_request", ir.correlation_request.kind.value)
    if ir.conditions:
        _add(
            "conditions",
            tuple(
                (condition.kind.value, condition.params) for condition in ir.conditions
            ),
        )
    return tuple(payload)


def _signal_from_ir(
    ir: CanonicalParserIR,
    metadata: MessageMetadata,
    identity: SignalIdentity,
    instruments: Mapping[str, Instrument],
) -> AdapterOutput:
    direction_fragment = _resolved_fragment(ir, CandidateSlot.DIRECTION)
    if direction_fragment is None:
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_DIRECTION_FRAGMENT_MISSING,
        )
    direction = direction_fragment.value
    if not isinstance(direction, TradeDirection):
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_DIRECTION_FRAGMENT_MISSING,
        )
    instrument_fragment = _resolved_fragment(ir, CandidateSlot.INSTRUMENT)
    if instrument_fragment is None:
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_INSTRUMENT_FRAGMENT_MISSING,
        )
    symbol = instrument_fragment.value
    instrument = (
        instruments.get(symbol)
        if isinstance(symbol, str) and symbol in instruments
        else None
    )
    if not isinstance(instrument, Instrument):
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_INSTRUMENT_UNMAPPED,
        )
    geometry_fragment = _resolved_fragment(ir, CandidateSlot.ENTRY_GEOMETRY)
    if geometry_fragment is None:
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_ENTRY_GEOMETRY_FRAGMENT_MISSING,
        )
    geometry = geometry_fragment.value
    if not isinstance(geometry, EntryGeometry):
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_ENTRY_GEOMETRY_FRAGMENT_MISSING,
        )

    entry_price: Price | None = None
    entry_range: PriceRange | None = None
    entry_levels: tuple[Price, ...] = ()
    entry_fragment = _resolved_fragment(ir, CandidateSlot.ENTRY)
    if entry_fragment is not None:
        value = entry_fragment.value
        if isinstance(value, Price):
            entry_price = value
        elif isinstance(value, PriceRange):
            entry_range = value
        elif isinstance(value, tuple):
            if len(value) == 1 and isinstance(value[0], Price):
                entry_price = value[0]
            elif len(value) == 1 and isinstance(value[0], PriceRange):
                entry_range = value[0]
            else:
                if not all(isinstance(item, Price) for item in value):
                    return AdapterOutput(
                        kind=AdapterOutputKind.NON_SIGNAL,
                        reason=REASON_ENTRY_LEVELS_SHAPE_NOT_REPRESENTABLE,
                    )
                entry_levels = value
        else:
            return AdapterOutput(
                kind=AdapterOutputKind.NON_SIGNAL,
                reason=REASON_ENTRY_VALUE_INVALID,
            )

    if geometry is EntryGeometry.MARKET and entry_price is not None:
        # Real corpus M24 (provider_014): MARKET trigger with the entry
        # price preserved. The Phase 1 Signal invariant forbids entry_price
        # under MARKET geometry. Surface the conflict; never drop the price
        # and never re-label the engine-derived geometry.
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_MARKET_GEOMETRY_WITH_ENTRY_NOT_REPRESENTABLE,
        )

    stop_loss: Price | None = None
    stop_loss_fragment = _resolved_fragment(ir, CandidateSlot.SL)
    if stop_loss_fragment is not None:
        if isinstance(stop_loss_fragment.value, Price):
            stop_loss = stop_loss_fragment.value
        else:
            return AdapterOutput(
                kind=AdapterOutputKind.NON_SIGNAL,
                reason=REASON_STOP_LOSS_RANGE_NOT_REPRESENTABLE,
            )

    take_profit_targets: tuple[Price, ...] = ()
    take_profit_fragment = _resolved_fragment(ir, CandidateSlot.TP)
    if take_profit_fragment is not None:
        if not isinstance(take_profit_fragment.value, tuple):
            return AdapterOutput(
                kind=AdapterOutputKind.NON_SIGNAL,
                reason=REASON_TAKE_PROFIT_VALUE_INVALID,
            )
        take_profit_targets = take_profit_fragment.value

    entry_trigger = EntryTrigger.UNSPECIFIED
    trigger_fragment = _resolved_fragment(ir, CandidateSlot.ENTRY_TRIGGER)
    if trigger_fragment is not None:
        if not isinstance(trigger_fragment.value, EntryTrigger):
            return AdapterOutput(
                kind=AdapterOutputKind.NON_SIGNAL,
                reason=REASON_ENTRY_TRIGGER_VALUE_INVALID,
            )
        entry_trigger = trigger_fragment.value

    signal = Signal(
        identity=identity,
        instrument=instrument,
        direction=direction,
        entry_geometry=geometry,
        entry_trigger=entry_trigger,
        created_at_utc=metadata.timestamp_utc,
        entry_price=entry_price,
        entry_range=entry_range,
        entry_levels=entry_levels,
        stop_loss=stop_loss,
        take_profit_targets=take_profit_targets,
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
    )
    return AdapterOutput(kind=AdapterOutputKind.SIGNAL, signal=signal)


def _instruction_from_ir(
    ir: CanonicalParserIR,
    action_fragment: ParsedFragment,
    metadata: MessageMetadata,
    identity: SignalIdentity,
) -> AdapterOutput:
    instruction_type = action_fragment.value
    if not isinstance(instruction_type, InstructionType):
        # The engine resolves ACTION values via CATEGORY_INSTRUCTION and can
        # only emit InstructionType members; a non-member value is an engine
        # contract violation and is refused, never coerced.
        return AdapterOutput(
            kind=AdapterOutputKind.NON_SIGNAL,
            reason=REASON_ACTION_VALUE_INVALID,
        )
    instruction = SignalInstruction(
        instruction_type=instruction_type,
        signal_identity=identity,
        created_at_utc=metadata.timestamp_utc,
        payload=_instruction_payload(ir, action_fragment),
    )
    return AdapterOutput(kind=AdapterOutputKind.INSTRUCTION, instruction=instruction)


def adapt_parse_result(
    result: ParseResult,
    *,
    metadata: MessageMetadata,
    identity: SignalIdentity,
    instruments: Mapping[str, Instrument] | None = None,
) -> AdapterOutput:
    """Convert a ``ParseResult`` into its explicit adapter output (§25 step 5).

    ``identity`` — caller-supplied ``SignalIdentity`` (design §4.4: identity
    UUIDs are produced by the integration layer, never by the parser). For
    INSTRUCTION outputs the caller-designated identity is used and the
    pending target resolution is recorded in the payload via the IR's
    ``correlation_request`` (correlation itself is Phase 3+, ADR 0006).

    ``instruments`` — caller-supplied symbol → ``Instrument`` resolution. The
    IR carries the canonical symbol STRING only (design §23 open question 8:
    no global symbol table, no AssetClass inference); a signal whose symbol
    is not mapped is returned as NON_SIGNAL(instrument_unmapped), never
    guessed.

    ``MULTI_SIGNAL`` results are refused (anti-merge rule, ADR 0013 §5):
    consumers MUST convert per-block content via the Phase 3+ correlation
    layer; this module never silently picks one block.
    """
    if not isinstance(result, ParseResult):
        raise TypeError("result must be ParseResult")
    if not isinstance(metadata, MessageMetadata):
        raise TypeError("metadata must be MessageMetadata")
    if not isinstance(identity, SignalIdentity):
        raise TypeError("identity must be SignalIdentity")
    if instruments is not None:
        if not isinstance(instruments, Mapping):
            raise TypeError("instruments must be a Mapping[str, Instrument] or None")
        for key, value in instruments.items():
            if not isinstance(key, str):
                raise TypeError("instruments keys must be str")
            if not isinstance(value, Instrument):
                raise TypeError("instruments values must be Instrument")

    if result.outcome is ParseResultState.PARSED:
        action_fragment = _resolved_fragment(result.ir, CandidateSlot.ACTION)
        if action_fragment is not None:
            return _instruction_from_ir(result.ir, action_fragment, metadata, identity)
        return _signal_from_ir(result.ir, metadata, identity, instruments or {})
    reason = _NON_SIGNAL_REASONS[result.outcome]
    return AdapterOutput(kind=AdapterOutputKind.NON_SIGNAL, reason=reason)
