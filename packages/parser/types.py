"""Phase 2 parser contract layer — frozen value objects and concept contracts.

Authoritative registry: `docs/phase-2-parser-engine-design.md` §26.2. Every type
here has EXACTLY the fields declared there; no extra fields and no undocumented
behaviour. Type validation follows the Phase 1 convention (raise on invalid
input in ``__post_init__``). This module contains NO parsing logic, NO regex
execution, NO normalization, NO candidate extraction, NO correlation, and NO
execution semantics.

Phase 1 enums are IMPORTED verbatim and never extended (design §4.3, §26.1).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from packages.parser.enums import (
    AmbiguityKind,
    BlockSeparatorKind,
    CandidateSlot,
    ConditionKind,
    ConflictKind,
    Constraint,
    ContextReferenceKind,
    ContextRequirement,
    CorrelationRequestKind,
    DeleteBehavior,
    EditBehavior,
    FollowUpBehavior,
    FragmentState,
    MatcherKind,
    MediaKind,
    MessageEvent,
    OccurrenceSelection,
    ParseResultState,
    ReplyRequirement,
    ScopeKind,
    SemanticTarget,
    TokenCategory,
)
from packages.signal_core.domain import SignalIdentity
from packages.signal_core.enums import SourceType


def _require_kv_pairs(value: object, name: str) -> None:
    """Validate a ``(str, object)`` pair tuple (provenance, params, fields)."""
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a frozen tuple of (str, object) pairs")
    for item in value:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"{name} must be a tuple of (str, object) pairs")
        if not isinstance(item[0], str):
            raise TypeError(f"{name} key must be str, got {type(item[0]).__name__}")


def _require_parsed_fragments(value: object, name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a frozen tuple of ParsedFragment")
    for i, fragment in enumerate(value):
        if not isinstance(fragment, ParsedFragment):
            raise TypeError(f"{name}[{i}] must be ParsedFragment")


# ---------------------------------------------------------------------------
# Supporting value objects (design §5.5.1, §7.2, §8.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Character offsets into the RAW text (design §5.5).

    ``start`` is inclusive, ``end`` is exclusive. Offsets are ALWAYS raw-text
    offsets; normalized offsets never appear in a ``SourceSpan`` (§5.5.1).
    """

    start: int
    end: int
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.start, int):
            raise TypeError("start must be int")
        if not isinstance(self.end, int):
            raise TypeError("end must be int")
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end < self.start:
            raise ValueError("end must be >= start")
        if self.source_reference is not None and not isinstance(
            self.source_reference, str
        ):
            raise TypeError("source_reference must be str or None")


@dataclass(frozen=True, slots=True)
class SourceMap:
    """Normalized <-> raw offset mapping (design §5.5.1, ADR 0012).

    ``char_ranges[i]`` is the ``(raw_start, raw_end)`` of the raw characters that
    produced normalized character ``i``. ``deleted_ranges`` are
    ``(raw_start, raw_end, op_name)`` triples for raw ranges removed by a named
    normalization op.

    Structural invariants enforced here: entry shapes are valid, raw starts are
    non-decreasing, and deleted ranges are ordered and non-overlapping. The
    cross-object invariants (``len(char_ranges) == len(normalized_text)`` and
    exact-once accounting of every raw offset) relate to ``raw_text`` /
    ``normalized_text`` and are validated by ``NormalizedMessage`` and Phase 3+
    tests respectively.
    """

    char_ranges: tuple[tuple[int, int], ...]
    deleted_ranges: tuple[tuple[int, int, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.char_ranges, tuple):
            raise TypeError("char_ranges must be a frozen tuple")
        prev_start = -1
        for i, entry in enumerate(self.char_ranges):
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise TypeError(f"char_ranges[{i}] must be a (raw_start, raw_end) pair")
            start, end = entry
            if not isinstance(start, int) or not isinstance(end, int):
                raise TypeError(f"char_ranges[{i}] offsets must be int")
            if start < 0 or end <= start:
                raise ValueError(
                    f"char_ranges[{i}] must have 0 <= start < end (non-empty raw range)"
                )
            if start < prev_start:
                raise ValueError(
                    f"char_ranges raw starts must be non-decreasing (index {i})"
                )
            prev_start = start

        if not isinstance(self.deleted_ranges, tuple):
            raise TypeError("deleted_ranges must be a frozen tuple")
        prev_end = -1
        for i, del_entry in enumerate(self.deleted_ranges):
            if not isinstance(del_entry, tuple) or len(del_entry) != 3:
                raise TypeError(
                    f"deleted_ranges[{i}] must be a (raw_start, raw_end, op_name) triple"
                )
            d_start, d_end, op_name = del_entry
            if not isinstance(d_start, int) or not isinstance(d_end, int):
                raise TypeError(f"deleted_ranges[{i}] offsets must be int")
            if not isinstance(op_name, str) or not op_name:
                raise ValueError(
                    f"deleted_ranges[{i}] op_name must be a non-empty string"
                )
            if d_start < 0 or d_end <= d_start:
                raise ValueError(f"deleted_ranges[{i}] must have 0 <= start < end")
            if d_start < prev_end:
                raise ValueError(
                    f"deleted_ranges must be ordered and non-overlapping (index {i})"
                )
            prev_end = d_end

    def raw_span_for(self, norm_start: int, norm_end: int) -> tuple[int, int]:
        """Project a non-empty normalized range to a raw-text interval (§5.5.1).

        Returns ``(raw_start, raw_end)`` — the minimal contiguous raw interval
        covering every raw source character of ``normalized_text[norm_start:norm_end]``.
        """
        if not isinstance(norm_start, int) or not isinstance(norm_end, int):
            raise TypeError("norm_start and norm_end must be int")
        if not (0 <= norm_start < norm_end <= len(self.char_ranges)):
            raise ValueError(
                f"invalid normalized range [{norm_start}, {norm_end}) "
                f"for char_ranges of length {len(self.char_ranges)}"
            )
        return (self.char_ranges[norm_start][0], self.char_ranges[norm_end - 1][1])


@dataclass(frozen=True, slots=True)
class MatcherSpec:
    """Declarative matcher for a ``ProviderRule`` (design §7.2)."""

    kind: MatcherKind
    params: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MatcherKind):
            raise TypeError("kind must be MatcherKind")
        _require_kv_pairs(self.params, "params")


@dataclass(frozen=True, slots=True)
class Anchor:
    """A token/keyword reference used by a ``ScopeSpec`` anchor (design §26.2).

    The design describes an anchor as a "token/keyword reference" (§5.5.1,
    §7.4). ``text`` is the referenced token/keyword text (e.g., the keyword
    ``"SL"`` for an ``AFTER_TOKEN`` scope). This is the resolved contract for
    ``Anchor``; a richer anchor taxonomy (if ever needed) is a Phase 3+ ADR.
    """

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("text must be str")


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """Declarative scope for a ``ProviderRule`` (design §7.2)."""

    kind: ScopeKind
    anchors: tuple[Anchor, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ScopeKind):
            raise TypeError("kind must be ScopeKind")
        if not isinstance(self.anchors, tuple):
            raise TypeError("anchors must be a frozen tuple")
        for i, anchor in enumerate(self.anchors):
            if not isinstance(anchor, Anchor):
                raise TypeError(f"anchors[{i}] must be Anchor")


@dataclass(frozen=True, slots=True)
class Condition:
    """Deterministic predicate, recorded but never evaluated (design §8.2)."""

    kind: ConditionKind
    params: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ConditionKind):
            raise TypeError("kind must be ConditionKind")
        _require_kv_pairs(self.params, "params")


# ---------------------------------------------------------------------------
# Message model (design §5.1-§5.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RawMessage:
    """Untouched provider payload (design §5.1).

    ``raw_payload_hash`` is derived (SHA-256 of ``raw_text``) and is a
    message-identity/dedup hash — DISTINCT from the canonical semantic
    fingerprint (design §5.1, §13.3). The caller-supplied value is ignored.
    """

    raw_text: str
    media_refs: tuple[MediaKind, ...]
    raw_payload_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.raw_text, str):
            raise TypeError("raw_text must be str")
        if not isinstance(self.media_refs, tuple):
            raise TypeError("media_refs must be a frozen tuple")
        for i, ref in enumerate(self.media_refs):
            if not isinstance(ref, MediaKind):
                raise TypeError(f"media_refs[{i}] must be MediaKind")
        object.__setattr__(
            self,
            "raw_payload_hash",
            hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class MessageMetadata:
    """Provider/source identity and message lifecycle (design §5.2)."""

    provider_name: str
    source_type: SourceType
    timestamp_utc: datetime
    message_event: MessageEvent
    source_reference: str | None = None
    reply_to: ContextReference | None = None
    provenance_extra: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provider_name, str) or not self.provider_name:
            raise ValueError("provider_name must be a non-empty string")
        if not isinstance(self.source_type, SourceType):
            raise TypeError("source_type must be SourceType")
        if not isinstance(self.timestamp_utc, datetime):
            raise TypeError("timestamp_utc must be datetime")
        if self.timestamp_utc.tzinfo is None:
            raise ValueError(
                "timestamp_utc must be timezone-aware; naive datetime rejected"
            )
        offset = self.timestamp_utc.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("timestamp_utc must be UTC-aware (utcoffset == 0)")
        if not isinstance(self.message_event, MessageEvent):
            raise TypeError("message_event must be MessageEvent")
        if self.source_reference is not None and not isinstance(
            self.source_reference, str
        ):
            raise TypeError("source_reference must be str or None")
        if self.reply_to is not None and not isinstance(
            self.reply_to, ContextReference
        ):
            raise TypeError("reply_to must be ContextReference or None")
        _require_kv_pairs(self.provenance_extra, "provenance_extra")


@dataclass(frozen=True, slots=True)
class NormalizedMessage:
    """Derived working view of a raw message (design §5.3)."""

    normalized_text: str
    source_map: SourceMap
    normalization_decisions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_text, str):
            raise TypeError("normalized_text must be str")
        if not isinstance(self.source_map, SourceMap):
            raise TypeError("source_map must be SourceMap")
        if len(self.source_map.char_ranges) != len(self.normalized_text):
            raise ValueError(
                "source_map.char_ranges length must equal normalized_text length"
            )
        if not isinstance(self.normalization_decisions, tuple):
            raise TypeError("normalization_decisions must be a frozen tuple")
        for i, decision in enumerate(self.normalization_decisions):
            if not isinstance(decision, str):
                raise TypeError(f"normalization_decisions[{i}] must be str")


@dataclass(frozen=True, slots=True)
class Token:
    """A single lexical unit (design §5.4)."""

    category: TokenCategory
    text: str
    source_span: SourceSpan

    def __post_init__(self) -> None:
        if not isinstance(self.category, TokenCategory):
            raise TypeError("category must be TokenCategory")
        if not isinstance(self.text, str):
            raise TypeError("text must be str")
        if not isinstance(self.source_span, SourceSpan):
            raise TypeError("source_span must be SourceSpan")


# ---------------------------------------------------------------------------
# Candidate model (design §5.6-§5.12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MatchEvidence:
    """Provenance record for a candidate / rule match / conflict (design §5.8)."""

    kind: str
    rule_id: str | None = None
    span: SourceSpan | None = None
    snippet: str | None = None
    fields: tuple[tuple[str, object], ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("kind must be a non-empty string")
        if self.rule_id is not None and not isinstance(self.rule_id, str):
            raise TypeError("rule_id must be str or None")
        if self.span is not None and not isinstance(self.span, SourceSpan):
            raise TypeError("span must be SourceSpan or None")
        if self.snippet is not None and not isinstance(self.snippet, str):
            raise TypeError("snippet must be str or None")
        _require_kv_pairs(self.fields, "fields")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be str or None")


@dataclass(frozen=True, slots=True)
class Candidate:
    """A competing hypothesis for one semantic slot (design §5.6)."""

    slot: CandidateSlot
    value: object
    source_span: SourceSpan
    provenance: tuple[MatchEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.slot, CandidateSlot):
            raise TypeError("slot must be CandidateSlot")
        if not isinstance(self.source_span, SourceSpan):
            raise TypeError("source_span must be SourceSpan")
        if not isinstance(self.provenance, tuple):
            raise TypeError("provenance must be a frozen tuple")
        for i, evidence in enumerate(self.provenance):
            if not isinstance(evidence, MatchEvidence):
                raise TypeError(f"provenance[{i}] must be MatchEvidence")


@dataclass(frozen=True, slots=True)
class CandidateGraph:
    """Multiple competing candidates per slot, preserved before resolution (§5.7)."""

    by_slot: tuple[tuple[CandidateSlot, tuple[Candidate, ...]], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.by_slot, tuple):
            raise TypeError("by_slot must be a frozen tuple")
        seen: set[CandidateSlot] = set()
        for slot, candidates in self.by_slot:
            if not isinstance(slot, CandidateSlot):
                raise TypeError("by_slot key must be CandidateSlot")
            if slot in seen:
                raise ValueError(f"by_slot contains duplicate slot {slot!r}")
            seen.add(slot)
            if not isinstance(candidates, tuple):
                raise TypeError("by_slot value must be a frozen tuple")
            for i, candidate in enumerate(candidates):
                if not isinstance(candidate, Candidate):
                    raise TypeError(f"candidates for slot {slot!r} must be Candidate")


@dataclass(frozen=True, slots=True)
class RuleMatch:
    """A rule that fired, with bound candidates (design §5.9)."""

    rule_id: str
    category: str
    span: SourceSpan
    bindings: tuple[tuple[str, Candidate], ...]
    evidence: tuple[MatchEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, str) or not self.rule_id:
            raise ValueError("rule_id must be a non-empty string")
        if not isinstance(self.category, str) or not self.category:
            raise ValueError("category must be a non-empty string")
        if not isinstance(self.span, SourceSpan):
            raise TypeError("span must be SourceSpan")
        _require_kv_pairs(self.bindings, "bindings")
        for slot_name, candidate in self.bindings:
            if not isinstance(candidate, Candidate):
                raise TypeError(f"bindings[{slot_name!r}] value must be Candidate")
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be a frozen tuple")
        for i, evidence in enumerate(self.evidence):
            if not isinstance(evidence, MatchEvidence):
                raise TypeError(f"evidence[{i}] must be MatchEvidence")


@dataclass(frozen=True, slots=True)
class Conflict:
    """Contradiction between non-compatible interpretations for the SAME slot (§5.10)."""

    kind: ConflictKind
    slot: CandidateSlot
    involved: tuple[Candidate, ...]
    spans: tuple[SourceSpan, ...]
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ConflictKind):
            raise TypeError("kind must be ConflictKind")
        if not isinstance(self.slot, CandidateSlot):
            raise TypeError("slot must be CandidateSlot")
        if not isinstance(self.involved, tuple):
            raise TypeError("involved must be a frozen tuple")
        for i, candidate in enumerate(self.involved):
            if not isinstance(candidate, Candidate):
                raise TypeError(f"involved[{i}] must be Candidate")
        if not isinstance(self.spans, tuple):
            raise TypeError("spans must be a frozen tuple")
        for i, span in enumerate(self.spans):
            if not isinstance(span, SourceSpan):
                raise TypeError(f"spans[{i}] must be SourceSpan")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")


@dataclass(frozen=True, slots=True)
class Ambiguity:
    """Genuine underdetermination, not a contradiction (design §5.11)."""

    kind: AmbiguityKind
    slot: CandidateSlot | None = None
    candidates: tuple[Candidate, ...] = ()
    spans: tuple[SourceSpan, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AmbiguityKind):
            raise TypeError("kind must be AmbiguityKind")
        if self.slot is not None and not isinstance(self.slot, CandidateSlot):
            raise TypeError("slot must be CandidateSlot or None")
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a frozen tuple")
        for i, candidate in enumerate(self.candidates):
            if not isinstance(candidate, Candidate):
                raise TypeError(f"candidates[{i}] must be Candidate")
        if not isinstance(self.spans, tuple):
            raise TypeError("spans must be a frozen tuple")
        for i, span in enumerate(self.spans):
            if not isinstance(span, SourceSpan):
                raise TypeError(f"spans[{i}] must be SourceSpan")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be str")


@dataclass(frozen=True, slots=True)
class ParsedFragment:
    """A partial semantic result for one aspect of a message (design §5.12)."""

    slot: CandidateSlot
    value: object
    state: FragmentState
    condition: tuple[Condition, ...] = ()
    evidence: tuple[MatchEvidence, ...] = ()
    context_requirement: ContextRequirement = ContextRequirement.NONE

    def __post_init__(self) -> None:
        if not isinstance(self.slot, CandidateSlot):
            raise TypeError("slot must be CandidateSlot")
        if not isinstance(self.state, FragmentState):
            raise TypeError("state must be FragmentState")
        if not isinstance(self.condition, tuple):
            raise TypeError("condition must be a frozen tuple")
        for i, condition in enumerate(self.condition):
            if not isinstance(condition, Condition):
                raise TypeError(f"condition[{i}] must be Condition")
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be a frozen tuple")
        for i, evidence in enumerate(self.evidence):
            if not isinstance(evidence, MatchEvidence):
                raise TypeError(f"evidence[{i}] must be MatchEvidence")
        if not isinstance(self.context_requirement, ContextRequirement):
            raise TypeError("context_requirement must be ContextRequirement")


# ---------------------------------------------------------------------------
# Context / correlation boundary + edit delta (design §5.20, §5.21, §9.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContextReference:
    """A reference to a prior message/signal (design §5.20)."""

    provider_name: str
    kind: ContextReferenceKind
    source_reference: str | None = None
    signal_identity: SignalIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider_name, str) or not self.provider_name:
            raise ValueError("provider_name must be a non-empty string")
        if not isinstance(self.kind, ContextReferenceKind):
            raise TypeError("kind must be ContextReferenceKind")
        if self.source_reference is not None and not isinstance(
            self.source_reference, str
        ):
            raise TypeError("source_reference must be str or None")
        if self.signal_identity is not None and not isinstance(
            self.signal_identity, SignalIdentity
        ):
            raise TypeError("signal_identity must be SignalIdentity or None")


@dataclass(frozen=True, slots=True)
class CorrelationRequest:
    """What the parser asks the correlation layer to do (design §5.21)."""

    kind: CorrelationRequestKind
    target: ContextReference | None = None
    fragments: tuple[ParsedFragment, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CorrelationRequestKind):
            raise TypeError("kind must be CorrelationRequestKind")
        if self.target is not None and not isinstance(self.target, ContextReference):
            raise TypeError("target must be ContextReference or None")
        _require_parsed_fragments(self.fragments, "fragments")


@dataclass(frozen=True, slots=True)
class EditDelta:
    """Delta representation of an edited message (design §9.2)."""

    added: tuple[ParsedFragment, ...]
    changed: tuple[tuple[ParsedFragment, ParsedFragment], ...]
    removed: tuple[ParsedFragment, ...]
    unchanged: tuple[ParsedFragment, ...]

    def __post_init__(self) -> None:
        _require_parsed_fragments(self.added, "added")
        _require_parsed_fragments(self.removed, "removed")
        _require_parsed_fragments(self.unchanged, "unchanged")
        if not isinstance(self.changed, tuple):
            raise TypeError("changed must be a frozen tuple")
        for i, pair in enumerate(self.changed):
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError(
                    f"changed[{i}] must be a (before, after) ParsedFragment pair"
                )
            before, after = pair
            if not isinstance(before, ParsedFragment):
                raise TypeError(f"changed[{i}][0] must be ParsedFragment")
            if not isinstance(after, ParsedFragment):
                raise TypeError(f"changed[{i}][1] must be ParsedFragment")


# ---------------------------------------------------------------------------
# Multi-block message model (ADR 0013)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MessageBlock:
    """One mechanically segmented section of a message (ADR 0013).

    ``norm_start``/``norm_end`` are offsets into the message's normalized
    text; ``raw_start``/``raw_end`` are the corresponding RAW offsets
    (SourceSpan semantics, inclusive start / exclusive end, computed via
    the message's SourceMap). The separator characters between blocks
    belong to no block. ``separator_kind`` records the boundary type that
    preceded the block (``NONE`` for the first block).
    """

    index: int
    norm_start: int
    norm_end: int
    raw_start: int
    raw_end: int
    separator_kind: BlockSeparatorKind

    def __post_init__(self) -> None:
        if not isinstance(self.index, int) or isinstance(self.index, bool):
            raise TypeError("index must be int")
        for name in ("norm_start", "norm_end", "raw_start", "raw_end"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be int")
        if self.index < 0:
            raise ValueError("index must be >= 0")
        if self.norm_start < 0 or self.raw_start < 0:
            raise ValueError("norm_start and raw_start must be >= 0")
        if self.norm_end <= self.norm_start:
            raise ValueError("norm_end must be > norm_start (non-empty block)")
        if self.raw_end <= self.raw_start:
            raise ValueError("raw_end must be > raw_start (non-empty raw span)")
        if not isinstance(self.separator_kind, BlockSeparatorKind):
            raise TypeError("separator_kind must be BlockSeparatorKind")


@dataclass(frozen=True, slots=True)
class BlockParse:
    """Per-block parse outcome and IR (ADR 0013).

    ``ir`` carries the block's full parse (fragments, conflicts,
    ambiguities, evidence) with global raw spans; provenance is
    block-scoped by containment. ``duplicate_of`` is the index of the
    FIRST block with an identical payload fingerprint (ADR 0013 §6) or
    None; it is comparison-only bookkeeping for future correlation — the
    parser never collapses duplicates.
    """

    block: MessageBlock
    outcome: ParseResultState
    ir: CanonicalParserIR
    duplicate_of: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.block, MessageBlock):
            raise TypeError("block must be MessageBlock")
        if not isinstance(self.outcome, ParseResultState):
            raise TypeError("outcome must be ParseResultState")
        if not isinstance(self.ir, CanonicalParserIR):
            raise TypeError("ir must be CanonicalParserIR")
        if self.duplicate_of is not None:
            if not isinstance(self.duplicate_of, int) or isinstance(
                self.duplicate_of, bool
            ):
                raise TypeError("duplicate_of must be int or None")
            if self.duplicate_of < 0 or self.duplicate_of >= self.block.index:
                raise ValueError("duplicate_of must reference an EARLIER block index")


# ---------------------------------------------------------------------------
# Canonical IR + ParseResult (design §13)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CanonicalParserIR:
    """Provider-syntax-free intermediate representation (design §13.2).

    Deliberately carries NO ``outcome`` field: the parse outcome has exactly one
    owner, ``ParseResult.outcome`` (§13.3).
    """

    candidates: tuple[Candidate, ...]
    unresolved_fields: tuple[CandidateSlot, ...]
    fragments: tuple[ParsedFragment, ...]
    conflicts: tuple[Conflict, ...]
    ambiguities: tuple[Ambiguity, ...]
    evidence: tuple[MatchEvidence, ...]
    normalization_decisions: tuple[str, ...]
    conditions: tuple[Condition, ...]
    provider_id: str
    parser_version: str
    context_reference: ContextReference | None = None
    correlation_request: CorrelationRequest | None = None
    source_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a frozen tuple")
        for i, candidate in enumerate(self.candidates):
            if not isinstance(candidate, Candidate):
                raise TypeError(f"candidates[{i}] must be Candidate")
        if not isinstance(self.unresolved_fields, tuple):
            raise TypeError("unresolved_fields must be a frozen tuple")
        for i, slot in enumerate(self.unresolved_fields):
            if not isinstance(slot, CandidateSlot):
                raise TypeError(f"unresolved_fields[{i}] must be CandidateSlot")
        _require_parsed_fragments(self.fragments, "fragments")
        if not isinstance(self.conflicts, tuple):
            raise TypeError("conflicts must be a frozen tuple")
        for i, conflict in enumerate(self.conflicts):
            if not isinstance(conflict, Conflict):
                raise TypeError(f"conflicts[{i}] must be Conflict")
        if not isinstance(self.ambiguities, tuple):
            raise TypeError("ambiguities must be a frozen tuple")
        for i, ambiguity in enumerate(self.ambiguities):
            if not isinstance(ambiguity, Ambiguity):
                raise TypeError(f"ambiguities[{i}] must be Ambiguity")
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be a frozen tuple")
        for i, evidence in enumerate(self.evidence):
            if not isinstance(evidence, MatchEvidence):
                raise TypeError(f"evidence[{i}] must be MatchEvidence")
        if not isinstance(self.normalization_decisions, tuple):
            raise TypeError("normalization_decisions must be a frozen tuple")
        for i, decision in enumerate(self.normalization_decisions):
            if not isinstance(decision, str):
                raise TypeError(f"normalization_decisions[{i}] must be str")
        if not isinstance(self.conditions, tuple):
            raise TypeError("conditions must be a frozen tuple")
        for i, condition in enumerate(self.conditions):
            if not isinstance(condition, Condition):
                raise TypeError(f"conditions[{i}] must be Condition")
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise ValueError("provider_id must be a non-empty string")
        if not isinstance(self.parser_version, str) or not self.parser_version:
            raise ValueError("parser_version must be a non-empty string")
        if self.context_reference is not None and not isinstance(
            self.context_reference, ContextReference
        ):
            raise TypeError("context_reference must be ContextReference or None")
        if self.correlation_request is not None and not isinstance(
            self.correlation_request, CorrelationRequest
        ):
            raise TypeError("correlation_request must be CorrelationRequest or None")
        if self.source_ref is not None and not isinstance(self.source_ref, str):
            raise TypeError("source_ref must be str or None")


@dataclass(frozen=True, slots=True)
class ParseResult:
    """The outcome wrapper returned by the parser (design §5.14).

    ``outcome`` is the SINGLE authoritative owner of the parse outcome; the IR
    carries no outcome field (§13.3). The Phase 2A contract is purely structural:
    the single owner plus the IR shape. The derived-outcome helper
    ``derive_outcome(ir)`` and the §14 decision procedure are Phase 3+ engine
    behaviour and are intentionally NOT part of this contract layer.

    ``blocks`` (ADR 0013): per-block parses for SECTIONED messages. ``None``
    means the legacy single-unit shape (every pre-2E message and every
    message whose profile declares no section dividers). For multi-block
    messages the top-level ``ir`` is an aggregate: the sole executable
    block's IR when exactly one block is PARSED, otherwise an explicitly
    empty IR whose evidence records the aggregation (§ ADR 0013 §5) —
    consumers MUST read ``blocks`` and never reassemble fragments across
    blocks.
    """

    outcome: ParseResultState
    ir: CanonicalParserIR
    blocks: tuple[BlockParse, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ParseResultState):
            raise TypeError("outcome must be ParseResultState")
        if not isinstance(self.ir, CanonicalParserIR):
            raise TypeError("ir must be CanonicalParserIR")
        if self.blocks is not None:
            if not isinstance(self.blocks, tuple):
                raise TypeError("blocks must be a frozen tuple or None")
            if len(self.blocks) < 2:
                raise ValueError(
                    "blocks must contain at least two entries (single-unit "
                    "parses keep blocks=None)"
                )
            for i, block_parse in enumerate(self.blocks):
                if not isinstance(block_parse, BlockParse):
                    raise TypeError(f"blocks[{i}] must be BlockParse")


# ---------------------------------------------------------------------------
# Provider architecture (design §5.15-§5.19, §7.2)
# ---------------------------------------------------------------------------


_CAPABILITY_FLAGS: tuple[str, ...] = (
    "close_full",
    "close_half",
    "profit_close",
    "move_sl_breakeven",
    "remove_sl",
    "cancel_pending",
    "trigger_pending",
    "move_sl_number",
    "move_sl_conditional",
    "move_tp_conditional",
    "move_entry_conditional",
    "edit_handling",
    "delete_handling",
    "reply_required",
    "negative_keywords",
    "last_signal_execution",
    "trailing",
    "multi_signal",
    "multi_message",
)


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """What a provider CAN express (design §5.16).

    Declared separately from ``ProviderRule`` (how it is parsed). Purely
    capability-oriented; never a mirror of provider syntax (§12.4). Exactly the
    19 documented boolean flags.
    """

    close_full: bool
    close_half: bool
    profit_close: bool
    move_sl_breakeven: bool
    remove_sl: bool
    cancel_pending: bool
    trigger_pending: bool
    move_sl_number: bool
    move_sl_conditional: bool
    move_tp_conditional: bool
    move_entry_conditional: bool
    edit_handling: bool
    delete_handling: bool
    reply_required: bool
    negative_keywords: bool
    last_signal_execution: bool
    trailing: bool
    multi_signal: bool
    multi_message: bool

    def __post_init__(self) -> None:
        for name in _CAPABILITY_FLAGS:
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class ProviderRule:
    """A single declarative parsing rule (design §7.2)."""

    id: str
    category: str
    matcher: MatcherSpec
    scope: ScopeSpec
    constraints: tuple[Constraint, ...]
    target: SemanticTarget
    priority: int
    occurrence: OccurrenceSelection

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("id must be a non-empty string")
        if not isinstance(self.category, str) or not self.category:
            raise ValueError("category must be a non-empty string")
        if not isinstance(self.matcher, MatcherSpec):
            raise TypeError("matcher must be MatcherSpec")
        if not isinstance(self.scope, ScopeSpec):
            raise TypeError("scope must be ScopeSpec")
        if not isinstance(self.constraints, tuple):
            raise TypeError("constraints must be a frozen tuple")
        for i, constraint in enumerate(self.constraints):
            if not isinstance(constraint, Constraint):
                raise TypeError(f"constraints[{i}] must be Constraint")
        if not isinstance(self.target, SemanticTarget):
            raise TypeError("target must be SemanticTarget")
        if not isinstance(self.priority, int):
            raise TypeError("priority must be int")
        if not isinstance(self.occurrence, OccurrenceSelection):
            raise TypeError("occurrence must be OccurrenceSelection")


class RuleSetResolutionError(ValueError):
    """Deterministic profile/RuleSet load error (design §12.5).

    ``code`` is the stable error identifier from §12.5. Phase 2A raises the
    construction-time codes only: ``"duplicate_rule_id"``,
    ``"exclusion_conflicts_with_declaration"``, ``"conflicting_override"``
    (override self-consistency). The chain-level codes — ``"rule_set_parent_missing"``,
    ``"rule_set_cycle"``, ``"exclusion_unknown_rule"`` — are reserved for the
    Phase 3+ profile loader (effective-RuleSet resolution), which is engine
    behaviour, not part of this contract layer.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RuleSet:
    """An ordered, inheritable collection of ``ProviderRule`` (design §5.18).

    The contract REPRESENTS everything the deterministic effective-RuleSet
    resolution (§12.5) needs: ``rules`` (provider rules), ``parent`` (single
    inherited RuleSet name), ``overrides`` (renamed masking pairs), and
    ``exclusions``. Rule identity is ``ProviderRule.id``; version compatibility
    is represented by ``ProviderProfile.version`` (§5.15), not by this type.

    Construction enforces the structural invariants that depend only on this
    ``RuleSet``'s own fields. The resolution ALGORITHM (linearization, folding,
    chain-level validation) is Phase 3+ engine behaviour and is not implemented
    here.
    """

    rules: tuple[ProviderRule, ...]
    parent: str | None = None
    overrides: tuple[tuple[str, str], ...] = ()
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.rules, tuple):
            raise TypeError("rules must be a frozen tuple")
        own_ids: set[str] = set()
        for i, rule in enumerate(self.rules):
            if not isinstance(rule, ProviderRule):
                raise TypeError(f"rules[{i}] must be ProviderRule")
            if rule.id in own_ids:
                raise RuleSetResolutionError(
                    "duplicate_rule_id",
                    f"duplicate rule id {rule.id!r} within one RuleSet",
                )
            own_ids.add(rule.id)

        if self.parent is not None and (
            not isinstance(self.parent, str) or not self.parent
        ):
            raise ValueError("parent must be a non-empty string or None")

        if not isinstance(self.overrides, tuple):
            raise TypeError("overrides must be a frozen tuple")
        seen_rule_ids: set[str] = set()
        seen_inherited_ids: set[str] = set()
        for override in self.overrides:
            if not isinstance(override, tuple) or len(override) != 2:
                raise TypeError(
                    "overrides entries must be (rule_id, inherited_rule_id) pairs"
                )
            rule_id, inherited_rule_id = override
            if not isinstance(rule_id, str) or not isinstance(inherited_rule_id, str):
                raise TypeError("override ids must be str")
            if rule_id not in own_ids:
                raise RuleSetResolutionError(
                    "conflicting_override",
                    f"override rule_id {rule_id!r} must be declared in this "
                    "RuleSet's own rules",
                )
            if rule_id in seen_rule_ids:
                raise RuleSetResolutionError(
                    "conflicting_override",
                    f"override rule_id {rule_id!r} appears more than once",
                )
            if inherited_rule_id in seen_inherited_ids:
                raise RuleSetResolutionError(
                    "conflicting_override",
                    f"override inherited_rule_id {inherited_rule_id!r} is targeted "
                    "more than once",
                )
            seen_rule_ids.add(rule_id)
            seen_inherited_ids.add(inherited_rule_id)

        if not isinstance(self.exclusions, tuple):
            raise TypeError("exclusions must be a frozen tuple")
        for excluded_id in self.exclusions:
            if not isinstance(excluded_id, str):
                raise TypeError("exclusions entries must be str")
            if excluded_id in own_ids:
                raise RuleSetResolutionError(
                    "exclusion_conflicts_with_declaration",
                    f"exclusion {excluded_id!r} names a rule declared in this "
                    "RuleSet's own rules",
                )
        if len(set(self.exclusions)) != len(self.exclusions):
            raise RuleSetResolutionError(
                "exclusion_conflicts_with_declaration",
                "exclusions contains duplicate entries",
            )


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    """Declarative definition of one provider (design §5.15)."""

    provider_name: str
    capabilities: ProviderCapabilities
    rule_set: RuleSet
    symbol_aliases: tuple[tuple[str, str], ...]
    tokenizer_pattern: str
    field_separators: tuple[str, ...]
    multi_value_separators: tuple[str, ...]
    decimal_format: str
    range_patterns: tuple[str, ...]
    multiline_mode: bool
    reply_requirement: ReplyRequirement
    edit_behavior: EditBehavior
    delete_behavior: DeleteBehavior
    follow_up_behavior: FollowUpBehavior
    version: str
    max_message_length: int = 8000
    max_numeric_value: Decimal = Decimal("1e12")
    section_dividers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provider_name, str) or not self.provider_name:
            raise ValueError("provider_name must be a non-empty string")
        if not isinstance(self.capabilities, ProviderCapabilities):
            raise TypeError("capabilities must be ProviderCapabilities")
        if not isinstance(self.rule_set, RuleSet):
            raise TypeError("rule_set must be RuleSet")
        if not isinstance(self.symbol_aliases, tuple):
            raise TypeError("symbol_aliases must be a frozen tuple")
        for i, pair in enumerate(self.symbol_aliases):
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError(f"symbol_aliases[{i}] must be a (alias, symbol) pair")
            if any(not isinstance(x, str) for x in pair):
                raise TypeError(f"symbol_aliases[{i}] values must be str")
        if not isinstance(self.tokenizer_pattern, str):
            raise TypeError("tokenizer_pattern must be str")
        if not isinstance(self.field_separators, tuple):
            raise TypeError("field_separators must be a frozen tuple")
        for i, sep in enumerate(self.field_separators):
            if not isinstance(sep, str):
                raise TypeError(f"field_separators[{i}] must be str")
        if not isinstance(self.multi_value_separators, tuple):
            raise TypeError("multi_value_separators must be a frozen tuple")
        for i, sep in enumerate(self.multi_value_separators):
            if not isinstance(sep, str):
                raise TypeError(f"multi_value_separators[{i}] must be str")
        if not isinstance(self.decimal_format, str):
            raise TypeError("decimal_format must be str")
        if not isinstance(self.range_patterns, tuple):
            raise TypeError("range_patterns must be a frozen tuple")
        for i, pattern in enumerate(self.range_patterns):
            if not isinstance(pattern, str):
                raise TypeError(f"range_patterns[{i}] must be str")
        if not isinstance(self.multiline_mode, bool):
            raise TypeError("multiline_mode must be bool")
        if not isinstance(self.reply_requirement, ReplyRequirement):
            raise TypeError("reply_requirement must be ReplyRequirement")
        if not isinstance(self.edit_behavior, EditBehavior):
            raise TypeError("edit_behavior must be EditBehavior")
        if not isinstance(self.delete_behavior, DeleteBehavior):
            raise TypeError("delete_behavior must be DeleteBehavior")
        if not isinstance(self.follow_up_behavior, FollowUpBehavior):
            raise TypeError("follow_up_behavior must be FollowUpBehavior")
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be a non-empty string")
        if not isinstance(self.max_message_length, int) or self.max_message_length <= 0:
            raise ValueError("max_message_length must be a positive int")
        if not isinstance(self.max_numeric_value, Decimal):
            raise TypeError("max_numeric_value must be Decimal")
        if self.max_numeric_value <= 0:
            raise ValueError("max_numeric_value must be > 0")
        if not isinstance(self.section_dividers, tuple):
            raise TypeError("section_dividers must be a frozen tuple")
        for i, divider in enumerate(self.section_dividers):
            if not isinstance(divider, str):
                raise TypeError(f"section_dividers[{i}] must be str")
            if not divider:
                raise ValueError(f"section_dividers[{i}] must be non-empty")
