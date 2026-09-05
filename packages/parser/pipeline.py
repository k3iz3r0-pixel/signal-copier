"""Pure parser pipeline stages (design §4.5, §4.6, §5.5.1, §6, §7, §14).

Every stage is a pure function; no I/O, no global state, no time, no
randomness (§4.4). The pipeline produces a :class:`ParseResult` whose
``outcome`` is the SINGLE owner of the parse outcome (§13.3) — the
outcome decision (§14.1/§14.2) lives here as engine behaviour and is
computed exactly once per parse.
"""

from __future__ import annotations

import unicodedata
from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from itertools import pairwise

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
    FragmentState,
    MatcherKind,
    MediaKind,
    MessageEvent,
    OccurrenceSelection,
    ParseResultState,
    ScopeKind,
    SemanticTarget,
    TokenCategory,
)
from packages.parser.profiles import ProfileRuntime
from packages.parser.safety import (
    BIDI_CONTROL_CHARS,
    DASH_VARIANTS,
    MARKDOWN_CHARS,
    MAX_CANDIDATES,
    MAX_DIGIT_RUN,
    MAX_NUMERIC_TOKENS_PER_FIELD,
    MAX_NUMERIC_TOKENS_PER_MESSAGE,
    MAX_RULE_MATCHES,
    REPETITION_RUN_LIMIT,
    ZERO_WIDTH_CHARS,
)
from packages.parser.types import (
    Ambiguity,
    Anchor,
    BlockParse,
    Candidate,
    CandidateGraph,
    CanonicalParserIR,
    Condition,
    Conflict,
    ContextReference,
    CorrelationRequest,
    MatchEvidence,
    MessageBlock,
    MessageMetadata,
    NormalizedMessage,
    ParsedFragment,
    ParseResult,
    ProviderRule,
    RawMessage,
    RuleMatch,
    SourceMap,
    SourceSpan,
    Token,
)
from packages.signal_core.enums import (
    EntryGeometry,
    EntryTrigger,
    InstructionType,
    TradeDirection,
)
from packages.signal_core.value_objects import Price, PriceRange

PARSER_VERSION = "2E.0.0"

# Action rule categories -> capability flag (§5.16, §12.4). Capability
# gating is engine-generic, never provider-specific.
CATEGORY_CAPABILITY: dict[str, str] = {
    "ACTION_CLOSE": "close_full",
    "ACTION_CLOSE_FULL": "close_full",
    "ACTION_PARTIAL_CLOSE": "close_half",
    "ACTION_BREAKEVEN": "move_sl_breakeven",
    "ACTION_REMOVE_SL": "remove_sl",
    "ACTION_CANCEL": "cancel_pending",
    "ACTION_TRIGGER": "trigger_pending",
    "ACTION_MOVE_SL": "move_sl_number",
    "ACTION_MOVE_SL_CONDITIONAL": "move_sl_conditional",
    "ACTION_MOVE_TP": "move_tp_conditional",
    "ACTION_MODIFY_ENTRY": "move_entry_conditional",
}

# Action rule categories -> canonical InstructionType (§8.1). The category
# (declared by the rule) is the authoritative semantic mapping; the rule's
# matcher only detects the provider's trigger phrase. The site_value (matched
# text or captured group) is preserved as a MatchEvidence snippet, NOT used
# to construct the InstructionType.
CATEGORY_INSTRUCTION: dict[str, InstructionType] = {
    "ACTION_CLOSE": InstructionType.CLOSE,
    "ACTION_CLOSE_FULL": InstructionType.CLOSE,
    "ACTION_PARTIAL_CLOSE": InstructionType.PARTIAL_CLOSE,
    "ACTION_BREAKEVEN": InstructionType.BREAKEVEN,
    "ACTION_REMOVE_SL": InstructionType.MOVE_SL,
    "ACTION_CANCEL": InstructionType.CANCEL,
    "ACTION_TRIGGER": InstructionType.MODIFY,
    "ACTION_MOVE_SL": InstructionType.MOVE_SL,
    "ACTION_MOVE_SL_CONDITIONAL": InstructionType.MOVE_SL,
    "ACTION_MOVE_TP": InstructionType.MOVE_TP,
    "ACTION_MODIFY_ENTRY": InstructionType.MODIFY,
}

# ProviderRule.target (SemanticTarget) -> CandidateSlot for pre-rule keyword
# candidate emission. Some SemanticTarget values (ENTRY_GEOMETRY, CONDITION,
# METADATA) do not correspond to a CandidateSlot the keyword-token extractor
# should emit, so they map to None.
_SEMANTIC_TO_CANDIDATE_SLOT: dict[str, CandidateSlot | None] = {
    "DIRECTION": CandidateSlot.DIRECTION,
    "INSTRUMENT": CandidateSlot.INSTRUMENT,
    "ENTRY": CandidateSlot.ENTRY,
    "ENTRY_GEOMETRY": None,
    "ENTRY_TRIGGER": CandidateSlot.ENTRY_TRIGGER,
    "SL": CandidateSlot.SL,
    "TP": CandidateSlot.TP,
    "ACTION": CandidateSlot.ACTION,
    "CONDITION": CandidateSlot.CONDITION,
    "METADATA": None,
}

# Slots where differing candidates are a CONTRADICTION (§5.10, §6.2).
# ENTRY_TRIGGER differences are AMBIGUITY instead (§6.2); TP is repeatable.
_CONFLICT_SLOTS = frozenset(
    {
        CandidateSlot.DIRECTION,
        CandidateSlot.INSTRUMENT,
        CandidateSlot.ENTRY,
        CandidateSlot.SL,
        CandidateSlot.ENTRY_GEOMETRY,
        CandidateSlot.ACTION,
        CandidateSlot.CONDITION,
        CandidateSlot.METADATA,
    }
)

_EMOJI_RANGES = ((0x1F000, 0x1FAFF), (0x2600, 0x27BF))


class _NormalizationRejected(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class _Violation:
    kind: str
    rule_id: str | None
    detail: str


@dataclass(frozen=True, slots=True)
class _Site:
    norm_start: int
    norm_end: int
    value: object
    match_start: int = 0
    match_end: int = 0


# ---------------------------------------------------------------------------
# Normalization (fixed §5.5.1 pipeline)
# ---------------------------------------------------------------------------


def _is_emoji(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _EMOJI_RANGES) or ch == "\ufe0f"


def normalize(raw_text: str, runtime: ProfileRuntime) -> NormalizedMessage:
    """Fixed normalization pipeline (§5.5.1). Raises _NormalizationRejected."""
    profile = runtime.profile
    if len(raw_text) > profile.max_message_length:
        raise _NormalizationRejected("message_too_long")
    for ch in raw_text:
        if ch not in "\t\n\r" and (ord(ch) < 0x20 or unicodedata.category(ch) == "Cc"):
            raise _NormalizationRejected("embedded_control_char")

    spans: list[tuple[int, int]] = [(i, i + 1) for i in range(len(raw_text))]
    text: list[str] = list(raw_text)
    deleted: list[tuple[int, int, str]] = []
    decisions: list[str] = []

    # 1. strip_control_only — zero-width then bidi (§5.5.1 step 1).
    for op_name, charset in (
        ("strip_zero_width", ZERO_WIDTH_CHARS),
        ("strip_bidi_control", BIDI_CONTROL_CHARS),
    ):
        kept_text: list[str] = []
        kept_spans: list[tuple[int, int]] = []
        changed = False
        for ch, span in zip(text, spans):
            if ch in charset:
                deleted.append((span[0], span[1], op_name))
                changed = True
                continue
            kept_text.append(ch)
            kept_spans.append(span)
        text, spans = kept_text, kept_spans
        if changed:
            decisions.append(op_name)

    # 2. unicode_normalize — per-character NFKC (§5.5.1 step 2).
    new_text: list[str] = []
    new_spans: list[tuple[int, int]] = []
    nfkc_changed = False
    for ch, span in zip(text, spans):
        expanded = unicodedata.normalize("NFKC", ch)
        if expanded != ch:
            nfkc_changed = True
        for out_ch in expanded:
            new_text.append(out_ch)
            new_spans.append(span)
    text, spans = new_text, new_spans
    if nfkc_changed:
        decisions.append("nfkc")

    # 3. strip_markdown_html — fixed syntax charset, content preserved.
    kept_text = []
    kept_spans = []
    changed = False
    for ch, span in zip(text, spans):
        if ch in MARKDOWN_CHARS:
            deleted.append((span[0], span[1], "strip_markdown"))
            changed = True
            continue
        kept_text.append(ch)
        kept_spans.append(span)
    text, spans = kept_text, kept_spans
    if changed:
        decisions.append("strip_markdown")

    # 4. collapse_whitespace — every run -> one U+0020 covering the run.
    kept_text = []
    kept_spans = []
    changed = False
    i = 0
    while i < len(text):
        if text[i].isspace():
            j = i
            while j < len(text) and text[j].isspace():
                j += 1
            kept_text.append(" ")
            kept_spans.append((spans[i][0], spans[j - 1][1]))
            changed = changed or (j - i) > 1
            i = j
        else:
            kept_text.append(text[i])
            kept_spans.append(spans[i])
            i += 1
    text, spans = kept_text, kept_spans
    if changed:
        decisions.append("collapse_whitespace")

    # 5. canonicalize_separators — dash variants -> field_separators[0].
    if profile.field_separators:
        canonical = profile.field_separators[0]
        variants: set[str] = set()
        for sep in tuple(profile.field_separators[1:]):
            if sep == canonical:
                continue
            for ch in sep:
                variants.add(ch)
        for ch in DASH_VARIANTS:
            if ch != canonical:
                variants.add(ch)
        kept_text = []
        kept_spans = []
        changed = False
        for ch, span in zip(text, spans):
            if ch in variants:
                for out_ch in canonical:
                    kept_text.append(out_ch)
                    kept_spans.append(span)
                changed = True
                continue
            kept_text.append(ch)
            kept_spans.append(span)
        text, spans = kept_text, kept_spans
        if changed:
            decisions.append("separator_canonicalization")

    # 6. Adversarial repetition bound (ADR 0007 item 9). Raw is never
    #    truncated; only the normalized view is.
    kept_text = []
    kept_spans = []
    changed = False
    i = 0
    while i < len(text):
        j = i
        while j < len(text) and text[j] == text[i]:
            j += 1
        run_length = j - i
        if run_length > REPETITION_RUN_LIMIT:
            for k in range(i + REPETITION_RUN_LIMIT, j):
                deleted.append((spans[k][0], spans[k][1], "repetition_truncation"))
            changed = True
        keep = min(run_length, REPETITION_RUN_LIMIT)
        kept_text.extend(text[i : i + keep])
        kept_spans.extend(spans[i : i + keep])
        i = j
    text, spans = kept_text, kept_spans
    if changed:
        decisions.append("repetition_truncation")

    if not text:
        if "strip_zero_width" in decisions:
            raise _NormalizationRejected("zero_width_only")
        if "strip_bidi_control" in decisions:
            raise _NormalizationRejected("bidi_control_only")
        raise _NormalizationRejected("empty_after_normalization")

    # Deletion ops run in pipeline order, so `deleted` entries from later
    # ops can precede entries from earlier ops in raw-offset terms. The
    # SourceMap contract (§5.5.1, ADR 0012) requires deleted_ranges ordered
    # and non-overlapping; ops delete pairwise-disjoint raw characters, so
    # the canonical raw-position order is the sorted order.
    deleted.sort(key=lambda entry: (entry[0], entry[1]))
    source_map = SourceMap(char_ranges=tuple(spans), deleted_ranges=tuple(deleted))
    return NormalizedMessage(
        normalized_text="".join(text),
        source_map=source_map,
        normalization_decisions=tuple(decisions),
    )


# ---------------------------------------------------------------------------
# Tokenization (§4.6, §5.4)
# ---------------------------------------------------------------------------


def _classify(
    token_text: str, symbols_upper: dict[str, str], keywords_lower: set[str]
) -> TokenCategory:
    if token_text[0].isdigit():
        return TokenCategory.NUMBER
    if token_text.isspace():
        return TokenCategory.WHITESPACE
    if all(_is_emoji(ch) for ch in token_text):
        return TokenCategory.EMOJI
    if token_text.upper() in symbols_upper:
        return TokenCategory.SYMBOL
    if token_text.lower() in keywords_lower:
        return TokenCategory.KEYWORD
    if token_text[0].isalpha():
        return TokenCategory.TEXT
    return TokenCategory.PUNCT


def tokenize(
    normalized: NormalizedMessage, runtime: ProfileRuntime
) -> tuple[tuple[tuple[int, int, Token], ...], tuple[_Violation, ...]]:
    """Lexical analysis. Returns (positioned tokens, violations).

    Each element is ``(norm_start, norm_end, token)``; the token carries the
    RAW SourceSpan (§5.5) computed via the SourceMap projection.
    """
    text = normalized.normalized_text
    smap = normalized.source_map
    symbols_upper = {k.upper(): v for k, v in runtime.symbol_table.items()}
    keywords_lower = {k.lower() for k in runtime.keyword_texts}

    violations: list[_Violation] = []
    run = 0
    for ch in text:
        if ch.isdigit():
            run += 1
            if run > MAX_DIGIT_RUN:
                violations.append(
                    _Violation("numeric_overflow", None, f"digit run > {MAX_DIGIT_RUN}")
                )
                break
        else:
            run = 0

    positioned: list[tuple[int, int, Token]] = []
    pos = 0
    while pos < len(text):
        match = runtime.tokenizer.match(text, pos)
        if match is None or match.end() <= match.start():
            raw_start, raw_end = smap.raw_span_for(pos, pos + 1)
            span = SourceSpan(start=raw_start, end=raw_end)
            positioned.append(
                (pos, pos + 1, Token(TokenCategory.PUNCT, text[pos], span))
            )
            pos += 1
            continue
        start, end = match.span()
        token_text = text[start:end]
        raw_start, raw_end = smap.raw_span_for(start, end)
        raw_span = SourceSpan(start=raw_start, end=raw_end)
        category = _classify(token_text, symbols_upper, keywords_lower)
        if category is TokenCategory.NUMBER:
            try:
                value = Decimal(token_text)
            except InvalidOperation:
                violations.append(
                    _Violation("numeric_overflow", None, f"unparsable {token_text!r}")
                )
            else:
                if value > runtime.profile.max_numeric_value:
                    violations.append(
                        _Violation(
                            "numeric_overflow",
                            None,
                            f"{token_text} > max_numeric_value",
                        )
                    )
        positioned.append((start, end, Token(category, token_text, raw_span)))
        pos = end
    return tuple(positioned), tuple(violations)


# ---------------------------------------------------------------------------
# Generic candidate extraction (§4.6, §5.6, §5.7)
# ---------------------------------------------------------------------------


# Slots whose candidates may be emitted from pre-rule keyword tokens, with
# canonical value conversion matching the rule-bound values (§5.7). Numeric
# field slots (ENTRY/SL/TP) are excluded: a keyword can never carry a price
# value, and a text-valued numeric-slot candidate would create phantom
# conflicts against Price-valued rule bindings.
_KEYWORD_CANDIDATE_SLOTS = frozenset(
    {
        CandidateSlot.DIRECTION,
        CandidateSlot.INSTRUMENT,
        CandidateSlot.ENTRY_TRIGGER,
        CandidateSlot.ACTION,
    }
)


def _keyword_candidate_value(
    slot: CandidateSlot, rule: ProviderRule, token_text: str
) -> object:
    """Canonical value for a keyword-token candidate, matching what the
    rule-bound candidate for the same token would carry (§6.2 duplicate)."""
    params = dict(rule.matcher.params)
    canonical_value = params.get("canonical")
    text = str(canonical_value) if isinstance(canonical_value, str) else token_text
    # Keyword classification is case-insensitive (§5.4); enum lookups must be
    # too — a raw token like "buy"/"Long" canonicalizes to the enum name.
    if slot is CandidateSlot.DIRECTION:
        return TradeDirection[text.upper()]
    if slot is CandidateSlot.ENTRY_TRIGGER:
        return EntryTrigger[text.upper()]
    if slot is CandidateSlot.ACTION:
        return CATEGORY_INSTRUCTION[rule.category]
    return text


def extract_candidates(
    positioned: tuple[tuple[int, int, Token], ...], runtime: ProfileRuntime
) -> tuple[CandidateGraph, dict[str, list[tuple[int, int]]], tuple[_Violation, ...]]:
    """Generic pre-rule candidates + keyword index (used by constraints)."""
    candidates: list[Candidate] = []
    violations: list[_Violation] = []
    keyword_index: dict[str, list[tuple[int, int]]] = {}
    max_value = runtime.profile.max_numeric_value
    numeric_count = 0

    keyword_slots: dict[str, tuple[CandidateSlot, ProviderRule]] = {}
    for rule in runtime.effective_rules:
        if rule.matcher.kind is MatcherKind.LITERAL:
            value = dict(rule.matcher.params).get("value")
            if isinstance(value, str):
                candidate_slot = _SEMANTIC_TO_CANDIDATE_SLOT.get(rule.target.name)
                if candidate_slot is not None and candidate_slot in (
                    _KEYWORD_CANDIDATE_SLOTS
                ):
                    keyword_slots.setdefault(value.lower(), (candidate_slot, rule))

    for _, _, token in positioned:
        if token.category is TokenCategory.NUMBER:
            numeric_count += 1
            if numeric_count > MAX_NUMERIC_TOKENS_PER_MESSAGE:
                violations.append(
                    _Violation(
                        "numeric_list_too_long",
                        None,
                        f"> {MAX_NUMERIC_TOKENS_PER_MESSAGE} numeric tokens",
                    )
                )
                continue
            value = Decimal(token.text)
            if value > max_value:
                continue
            candidates.append(
                Candidate(
                    slot=CandidateSlot.PRICE,
                    value=value,
                    source_span=token.source_span,
                    provenance=(
                        MatchEvidence(kind="number_token", span=token.source_span),
                    ),
                )
            )
        elif token.category is TokenCategory.SYMBOL:
            candidates.append(
                Candidate(
                    slot=CandidateSlot.INSTRUMENT,
                    value=runtime.symbol_table[token.text.upper()],
                    source_span=token.source_span,
                    provenance=(
                        MatchEvidence(kind="symbol_token", span=token.source_span),
                    ),
                )
            )
        elif token.category is TokenCategory.KEYWORD:
            keyword_index.setdefault(token.text.lower(), []).append((0, 0))
            keyword_entry = keyword_slots.get(token.text.lower())
            if keyword_entry is not None:
                slot, rule = keyword_entry
                candidates.append(
                    Candidate(
                        slot=slot,
                        value=_keyword_candidate_value(slot, rule, token.text),
                        source_span=token.source_span,
                        provenance=(
                            MatchEvidence(kind="keyword_token", span=token.source_span),
                        ),
                    )
                )

    if len(candidates) > MAX_CANDIDATES:
        violations.append(
            _Violation(
                "candidate_limit_exceeded", None, f"{len(candidates)} candidates"
            )
        )
        candidates = candidates[:MAX_CANDIDATES]

    by_slot: dict[CandidateSlot, list[Candidate]] = {}
    for candidate in candidates:
        by_slot.setdefault(candidate.slot, []).append(candidate)
    graph_entries = tuple(
        (slot, tuple(sorted(cands, key=_candidate_order)))
        for slot, cands in sorted(by_slot.items(), key=lambda kv: kv[0].name)
    )
    return (
        CandidateGraph(by_slot=graph_entries),
        keyword_index,
        tuple(violations),
    )


def _candidate_order(candidate: Candidate) -> tuple[int, int, int]:
    return (
        candidate.source_span.start,
        candidate.source_span.end,
        len(candidate.provenance),
    )


# ---------------------------------------------------------------------------
# Rule evaluation (§7)
# ---------------------------------------------------------------------------


def _disqualified_numeric_starts(
    positioned: tuple[tuple[int, int, Token], ...], glue: frozenset[str]
) -> frozenset[int]:
    """Normalized start offsets of numeric tokens that are NOT price-eligible.

    Generic structural rules (§5.6 semantic binding — a number is not a
    price merely because it appears near a signal):

    - a number immediately followed by a percent sign (``2%``) is a
      percentage, never a price;
    - numbers joined into a chain of THREE or more numbers by a single
      non-glue punctuation token (``2026-09-05``, ``1,100,000``) are not
      standalone prices and the chain is not a two-part range.

    Disqualified numbers are preserved as unbound PRICE candidates; they are
    only excluded from semantic field binding.
    """
    disqualified: set[int] = set()
    number_indexes = [
        i
        for i, (_, _, token) in enumerate(positioned)
        if token.category is TokenCategory.NUMBER
    ]

    # percent-suffixed numbers
    for i in number_indexes:
        for j in range(i + 1, len(positioned)):
            token = positioned[j][2]
            if token.category is TokenCategory.WHITESPACE:
                continue
            if token.category is TokenCategory.PUNCT and token.text == "%":
                disqualified.add(positioned[i][0])
            break

    # chains of numbers connected by single non-glue punctuation
    chain_groups: list[list[int]] = []
    current: list[int] = []
    for prev_index, next_index in pairwise(number_indexes):
        between = [
            positioned[k][2]
            for k in range(prev_index + 1, next_index)
            if positioned[k][2].category is not TokenCategory.WHITESPACE
        ]
        connected = (
            len(between) == 1
            and between[0].category is TokenCategory.PUNCT
            and all(ch not in glue for ch in between[0].text)
        )
        if connected:
            if not current:
                current.append(prev_index)
            current.append(next_index)
        else:
            if len(current) >= 3:
                chain_groups.append(current)
            current = []
    if len(current) >= 3:
        chain_groups.append(current)
    for group in chain_groups:
        for index in group:
            disqualified.add(positioned[index][0])
    return frozenset(disqualified)


def _site_is_price_like(site: _Site, runtime: ProfileRuntime) -> bool:
    """True when a site's value denotes a number: either a typed numeric
    value (Decimal / Price / PriceRange from number and range matchers) or
    a regex capture whose text matches the profile's number pattern. Regex
    captures are strings, so the text shape decides — this keeps claims and
    price-eligibility uniform across matcher kinds."""
    if isinstance(site.value, (Decimal, Price, PriceRange)):
        return True
    return (
        isinstance(site.value, str)
        and runtime.number_pattern.fullmatch(site.value) is not None
    )


def _core_adjacent_starts(
    positioned: tuple[tuple[int, int, Token], ...], glue: frozenset[str]
) -> frozenset[int]:
    """Normalized start offsets of numeric tokens directly attached to the
    signal core: walking backwards over glue only, a SYMBOL token is
    reached before any content token. A number separated from the
    instrument by prose (or generic punctuation) is not core-adjacent and
    cannot be bound by a keyword-less whole-message rule (§5.6)."""
    adjacent: set[int] = set()
    for i, (norm_start, _norm_end, token) in enumerate(positioned):
        if token.category is not TokenCategory.NUMBER:
            continue
        for j in range(i - 1, -1, -1):
            neighbor = positioned[j][2]
            if _is_glue_token(neighbor, glue):
                continue
            if neighbor.category is TokenCategory.SYMBOL:
                adjacent.add(norm_start)
            break
    return frozenset(adjacent)


def evaluate_rules(
    positioned: tuple[tuple[int, int, Token], ...],
    normalized: NormalizedMessage,
    metadata: MessageMetadata,
    runtime: ProfileRuntime,
    raw_text: str,
    unit_bounds: tuple[int, int] | None = None,
    line_windows: tuple[tuple[int, int], ...] | None = None,
) -> tuple[
    tuple[RuleMatch, ...],
    tuple[_Violation, ...],
    tuple[_Violation, ...],
    tuple[Candidate, ...],
]:
    """Evaluate effective rules in §7.3 order. Returns (matches, violations,
    unsupported-feature records, alternative candidates).

    ``unit_bounds`` (ADR 0013): when given, the evaluation unit is the
    normalized range ``[unit_bounds[0], unit_bounds[1])`` (one message
    block) — WHOLE_MESSAGE scope covers the unit, not the whole message.
    ``None`` (default) evaluates the whole message exactly as before.
    ``line_windows`` (ADR 0013): precomputed LINE-scope windows, already
    clipped to the unit; ``None`` computes full-message windows.

    Semantic binding architecture (§5.6, §6.1):

    - a pre-pass computes the scoped windows (bounded value zones) and the
      matcher sites for every rule BEFORE any binding, so field claims are
      known to every rule;
    - a numeric site binds to a rule's target only if it is AUTHORIZED:
      it lies in the rule's bounded value zone, it is not claimed by a
      rule with a different semantic target (zone rules) or by any rule
      with a non-ENTRY target (keyword-less whole-message rules), it is
      not disqualified (percent/numeric-chain forms), and keyword-less
      whole-message numeric rules additionally require core adjacency to
      the instrument;
    - EVERY authorized site is bound as a candidate. The sites selected by
      the rule's ``occurrence`` become the RuleMatch bindings; ALL site
      candidates (selected and non-selected) are returned so the
      CandidateGraph is the authoritative pre-resolution candidate store
      (§5.7, §6.1) — no candidate is silently discarded because it
      appeared second.
    """
    text = normalized.normalized_text
    smap = normalized.source_map
    capabilities = runtime.profile.capabilities
    glue = _glue_characters(runtime)
    disqualified = _disqualified_numeric_starts(positioned, glue)
    core_adjacent = _core_adjacent_starts(positioned, glue)
    matches: list[RuleMatch] = []
    violations: list[_Violation] = []
    unsupported: list[_Violation] = []
    site_candidates: list[Candidate] = []
    fired_groups: set[str] = set()

    # --- pre-pass: scoped windows + matcher sites for every rule -----------
    if line_windows is None:
        line_windows = _line_windows(raw_text, normalized)
    prepass: list[
        tuple[ProviderRule, dict[str, object], list[_Site], list[tuple[int, int]], bool]
    ] = []
    for rule in runtime.effective_rules:
        params = dict(rule.matcher.params)
        windows = _scope_windows(
            rule, positioned, text, glue, line_windows, unit_bounds
        )
        anchor_dependent = rule.scope.kind in _ANCHOR_SCOPES
        sites = (
            _match_sites(rule, params, windows, text, positioned, runtime, disqualified)
            if windows
            else []
        )
        prepass.append((rule, params, sites, windows, anchor_dependent))

    # --- semantic claims (§5.6) --------------------------------------------
    # Zone-anchored numeric fields OWN their value zone. Ownership is
    # assigned in §7.3 precedence order (priority ascending, rule_id
    # lexicographic): a numeric site belongs to the highest-precedence
    # zone rule that covers it, and a zone rule may not bind a number
    # owned by a rule with a DIFFERENT target (e.g. the entry zone must
    # not re-bind the SL value, and the SL rule keeps its own value even
    # when a later entry zone also covers it).
    owned: dict[int, str] = {}
    zone_rules = [
        (rule, sites)
        for rule, _params, sites, _windows, anchor_dependent in prepass
        if anchor_dependent
    ]
    for rule, sites in sorted(
        zone_rules, key=lambda pair: (pair[0].priority, pair[0].id)
    ):
        for site in sites:
            if (
                isinstance(site.value, (Decimal, Price, PriceRange))
                and site.norm_start not in owned
            ):
                owned[site.norm_start] = rule.target.name

    # Keyword-less whole-message numeric rules may only bind numbers not
    # claimed by ANY rule with a non-ENTRY target (explicit fields, action
    # and condition captures). Regex captures carry their value as text, so
    # numeric-looking captures claim too — otherwise a regex rule would be
    # the only stakeholder of a number while every other rule treats it as
    # unclaimed.
    global_claims: set[int] = set()
    for rule, _params, sites, _windows, _anchor_dependent in prepass:
        if rule.target is SemanticTarget.ENTRY:
            continue
        global_claims.update(
            site.norm_start for site in sites if _site_is_price_like(site, runtime)
        )

    def _is_numeric_site(site: _Site) -> bool:
        return isinstance(site.value, (Decimal, Price, PriceRange))

    def _price_semantic_target(rule: ProviderRule, params: dict[str, object]) -> bool:
        if rule.target in (
            SemanticTarget.ENTRY,
            SemanticTarget.SL,
            SemanticTarget.TP,
        ):
            return True
        return (
            rule.target is SemanticTarget.CONDITION
            and str(params.get("condition_kind")) == "AT_PRICE"
        )

    for rule, params, sites, windows, anchor_dependent in prepass:
        capability = CATEGORY_CAPABILITY.get(rule.category)
        if capability is not None and not getattr(capabilities, capability):
            unsupported.append(
                _Violation(
                    "unsupported_feature", rule.id, f"capability {capability} is off"
                )
            )
            continue

        if anchor_dependent and not windows:
            if Constraint.REQUIRED in rule.constraints:
                violations.append(
                    _Violation(
                        "grammar_violation_missing_number",
                        rule.id,
                        f"anchor {tuple(a.text for a in rule.scope.anchors)} not found",
                    )
                )
            continue

        price_semantic = _price_semantic_target(rule, params)
        authorized: list[_Site] = []
        for site in sites:
            numeric_typed = _is_numeric_site(site)
            if (
                price_semantic
                and (numeric_typed or _site_is_price_like(site, runtime))
                and site.norm_start in disqualified
            ):
                # A percent form or a ≥3-number chain is never a price
                # operand — it cannot satisfy a numeric field or an
                # AT_PRICE condition (§5.6). It stays a preserved PRICE
                # candidate and may still feed non-price semantic targets
                # (e.g. a percent close action operand).
                continue
            if numeric_typed:
                if anchor_dependent:
                    owner = owned.get(site.norm_start)
                    if owner is not None and owner != rule.target.name:
                        continue
                else:
                    if site.norm_start in global_claims:
                        continue
                    if (
                        rule.matcher.kind
                        in (
                            MatcherKind.NUMBER,
                            MatcherKind.PRICE,
                            MatcherKind.PRICE_RANGE,
                        )
                        and site.norm_start not in core_adjacent
                    ):
                        continue
            authorized.append(site)

        if not authorized:
            if Constraint.REQUIRED in rule.constraints:
                violations.append(
                    _Violation(
                        "grammar_violation_missing_number",
                        rule.id,
                        "anchor matched but extraction target absent",
                    )
                )
            continue

        if not _constraints_pass(rule, params, metadata, positioned):
            continue
        if Constraint.MUTUALLY_EXCLUSIVE in rule.constraints:
            group = str(params.get("group", rule.category))
            if group in fired_groups:
                unsupported.append(
                    _Violation(
                        "mutually_exclusive_suppressed", rule.id, f"group {group}"
                    )
                )
                continue
            fired_groups.add(group)

        if len(authorized) > MAX_NUMERIC_TOKENS_PER_FIELD:
            violations.append(
                _Violation(
                    "numeric_list_too_long",
                    rule.id,
                    f"> {MAX_NUMERIC_TOKENS_PER_FIELD} per field",
                )
            )
            authorized = authorized[:MAX_NUMERIC_TOKENS_PER_FIELD]

        bound_candidates: list[tuple[_Site, Candidate]] = []
        for site in authorized:
            value_start, value_end = smap.raw_span_for(site.norm_start, site.norm_end)
            candidate = _bind_candidate(
                rule, site.value, SourceSpan(start=value_start, end=value_end)
            )
            bound_candidates.append((site, candidate))

        selected = _select_occurrences(
            rule, params, [site for site, _ in bound_candidates]
        )
        selected_ids = {id(site) for site in selected}
        emitted = 0
        for site, candidate in bound_candidates:
            site_candidates.append(candidate)
            if id(site) in selected_ids:
                if emitted >= MAX_RULE_MATCHES:
                    violations.append(
                        _Violation(
                            "rule_match_limit_exceeded",
                            None,
                            f"> {MAX_RULE_MATCHES} matches",
                        )
                    )
                    break
                match_start, match_end = smap.raw_span_for(
                    site.match_start, site.match_end
                )
                matches.append(
                    RuleMatch(
                        rule_id=rule.id,
                        category=rule.category,
                        span=SourceSpan(start=match_start, end=match_end),
                        bindings=((rule.target.name, candidate),),
                        evidence=(
                            MatchEvidence(
                                kind="rule_match",
                                rule_id=rule.id,
                                span=SourceSpan(start=match_start, end=match_end),
                                fields=(("priority", rule.priority),),
                            ),
                        ),
                    )
                )
                emitted += 1
            continue

    if len(site_candidates) > MAX_CANDIDATES:
        violations.append(
            _Violation(
                "candidate_limit_exceeded", None, f"{len(site_candidates)} candidates"
            )
        )
        site_candidates = site_candidates[:MAX_CANDIDATES]

    return (
        tuple(matches),
        tuple(violations),
        tuple(unsupported),
        tuple(site_candidates),
    )


_ANCHOR_SCOPES = frozenset(
    {
        ScopeKind.AFTER_TOKEN,
        ScopeKind.BEFORE_TOKEN,
        ScopeKind.BETWEEN_ANCHORS,
        ScopeKind.SECTION,
    }
)

# Numeric field targets; the ENTRY target is the fallback claimant (§5.6,
# semantic binding): every other numeric field (SL, TP, condition, action
# operands) CLAIMS the numeric sites it binds, and keyword-less entry rules
# may only bind unclaimed numbers.
_NUMERIC_SLOTS = frozenset({CandidateSlot.ENTRY, CandidateSlot.SL, CandidateSlot.TP})


def _glue_characters(runtime: ProfileRuntime) -> frozenset[str]:
    """Characters that may separate a field anchor from / inside its value
    zone: declared field separators and multi-value separators. Generic
    punctuation is NOT glue — a value zone stops at it, so unrelated
    content after a field (e.g. prose or phone numbers) is never absorbed."""
    chars: set[str] = set()
    profile = runtime.profile
    for separator in tuple(profile.field_separators) + tuple(
        profile.multi_value_separators
    ):
        chars.update(separator)
    return frozenset(chars)


def _is_glue_token(token: Token, glue: frozenset[str]) -> bool:
    if token.category is TokenCategory.WHITESPACE:
        return True
    return bool(token.text) and all(ch in glue for ch in token.text)


def _find_anchors(
    anchor: Anchor, positioned: tuple[tuple[int, int, Token], ...]
) -> list[tuple[int, int]]:
    """ALL occurrences of the anchor text (deterministic order)."""
    target = anchor.text.lower()
    found: list[tuple[int, int]] = []
    for norm_start, norm_end, token in positioned:
        if token.text.lower() == target and token.category in (
            TokenCategory.KEYWORD,
            TokenCategory.SYMBOL,
            TokenCategory.TEXT,
        ):
            found.append((norm_start, norm_end))
    return found


def _line_windows(
    raw_text: str, normalized: NormalizedMessage
) -> tuple[tuple[int, int], ...]:
    """Normalized windows that each lie within ONE raw line (scope ``line``,
    design §7.1).

    Whitespace collapse (§5.5 step 4) erases line structure from the
    normalized text — every whitespace run, including newlines, becomes one
    canonical space — so line boundaries are recovered from the SourceMap:
    a normalized character whose raw projection contains a raw line
    terminator (LF or CR) is a boundary and belongs to NO window. A
    LINE-scoped rule matches only inside these windows, which keeps every
    match entirely within one raw line of the original message.
    """
    text = normalized.normalized_text
    if not text:
        return ()
    boundaries: list[int] = []
    for index, (raw_start, raw_end) in enumerate(normalized.source_map.char_ranges):
        chunk = raw_text[raw_start:raw_end]
        if "\n" in chunk or "\r" in chunk:
            boundaries.append(index)
    windows: list[tuple[int, int]] = []
    start = 0
    for boundary in boundaries:
        if start < boundary:
            windows.append((start, boundary))
        start = boundary + 1
    if start < len(text):
        windows.append((start, len(text)))
    return tuple(windows)


def _scope_windows(
    rule: ProviderRule,
    positioned: tuple[tuple[int, int, Token], ...],
    text: str,
    glue: frozenset[str],
    line_windows: tuple[tuple[int, int], ...],
    unit_bounds: tuple[int, int] | None = None,
) -> list[tuple[int, int]]:
    """Scope windows for a rule.

    Anchor-relative scopes (AFTER_TOKEN / BEFORE_TOKEN) produce one BOUNDED
    value zone per anchor occurrence: the zone extends only over glue
    (whitespace, declared separators) and numeric value tokens and stops at
    the first non-value token. A field value must therefore be directly
    attached to its anchor — arbitrary later content (prose, phone numbers,
    other fields) is never part of the zone (§7.4 adjacency semantics).

    LINE windows are the raw-line segments computed once per message by
    :func:`_line_windows` (scope ``line``, design §7.1). In per-block
    evaluation (ADR 0013) the caller passes unit-clipped windows and
    ``unit_bounds``; WHOLE_MESSAGE then covers the evaluation unit instead
    of the whole message.
    """
    kind = rule.scope.kind
    if kind is ScopeKind.WHOLE_MESSAGE:
        if unit_bounds is not None:
            return [unit_bounds]
        return [(0, len(text))]
    if kind is ScopeKind.LINE:
        return list(line_windows)
    if kind in (ScopeKind.BETWEEN_ANCHORS, ScopeKind.SECTION):
        if len(rule.scope.anchors) < 2:
            return []
        first = _find_anchors(rule.scope.anchors[0], positioned)
        second = _find_anchors(rule.scope.anchors[1], positioned)
        if not first or not second:
            return []
        head, tail = first[0], second[0]
        if kind is ScopeKind.BETWEEN_ANCHORS:
            if head[1] > tail[0]:
                return []
            return [(head[1], tail[0])]
        if head[0] > tail[0]:
            return []
        return [(head[0], tail[1])]
    if kind is ScopeKind.AFTER_TOKEN:
        if not rule.scope.anchors:
            return []
        windows = []
        for _anchor_start, anchor_end in _find_anchors(
            rule.scope.anchors[0], positioned
        ):
            window_end = anchor_end
            for norm_start, norm_end, token in positioned:
                if norm_start < anchor_end:
                    continue
                if norm_start > window_end:
                    break  # gap; the zone cannot span it
                if token.category is TokenCategory.NUMBER or _is_glue_token(
                    token, glue
                ):
                    window_end = norm_end
                    continue
                break
            windows.append((anchor_end, window_end))
        return windows
    if kind is ScopeKind.BEFORE_TOKEN:
        if not rule.scope.anchors:
            return []
        windows = []
        for anchor_start, _anchor_end in _find_anchors(
            rule.scope.anchors[0], positioned
        ):
            window_start = anchor_start
            for norm_start, norm_end, token in reversed(positioned):
                if norm_end > anchor_start:
                    continue
                if norm_end < window_start:
                    break  # gap; the zone cannot span it
                if token.category is TokenCategory.NUMBER or _is_glue_token(
                    token, glue
                ):
                    window_start = norm_start
                    continue
                break
            if window_start < anchor_start:
                windows.append((window_start, anchor_start))
        return windows
    return []


def _match_sites(
    rule: ProviderRule,
    params: dict[str, object],
    windows: list[tuple[int, int]],
    text: str,
    positioned: tuple[tuple[int, int, Token], ...],
    runtime: ProfileRuntime,
    disqualified: frozenset[int],
) -> list[_Site]:
    kind = rule.matcher.kind
    sites: list[_Site] = []
    for win_start, win_end in windows:
        if kind is MatcherKind.LITERAL:
            value = str(params.get("value", ""))
            ignore_case = bool(params.get("ignore_case", True))
            needle = value.lower() if ignore_case else value
            for norm_start, norm_end, token in positioned:
                if not (win_start <= norm_start and norm_end <= win_end):
                    continue
                matched = (
                    token.text.lower() == needle
                    if ignore_case
                    else token.text == needle
                )
                if matched and token.category in (
                    TokenCategory.KEYWORD,
                    TokenCategory.TEXT,
                    TokenCategory.SYMBOL,
                ):
                    sites.append(
                        _Site(norm_start, norm_end, token.text, norm_start, norm_end)
                    )
        elif kind is MatcherKind.REGEX:
            pattern = runtime.rule_patterns.get(rule.id)
            if pattern is None:
                continue
            for match in pattern.finditer(text, win_start, win_end):
                default_group: int = 1 if pattern.groups else 0
                raw_group = params.get("group", default_group)
                group_index = (
                    int(raw_group)
                    if isinstance(raw_group, (int, float))
                    else default_group
                )
                if group_index > pattern.groups:
                    continue
                captured = match.group(group_index)
                if captured is None:
                    continue
                # §5.5 span contract: the site VALUE span is the captured
                # group's span, not the whole-match span, so the semantic
                # capture's SourceSpan points at the exact raw characters
                # extracted. The whole-match span is kept separately for the
                # §7.3 rule-overlap precedence.
                group_start, group_end = match.span(group_index)
                if group_end <= group_start:
                    continue
                sites.append(
                    _Site(
                        group_start,
                        group_end,
                        captured,
                        match.start(),
                        match.end(),
                    )
                )
        elif kind in (MatcherKind.SYMBOL, MatcherKind.ALIAS):
            for norm_start, norm_end, token in positioned:
                if not (win_start <= norm_start and norm_end <= win_end):
                    continue
                if token.category is TokenCategory.SYMBOL:
                    canonical = runtime.symbol_table.get(token.text.upper())
                    if canonical is not None:
                        sites.append(
                            _Site(norm_start, norm_end, canonical, norm_start, norm_end)
                        )
        elif kind in (MatcherKind.NUMBER, MatcherKind.PRICE):
            for norm_start, norm_end, token in positioned:
                if not (win_start <= norm_start and norm_end <= win_end):
                    continue
                if token.category is TokenCategory.NUMBER:
                    sites.append(
                        _Site(
                            norm_start,
                            norm_end,
                            Decimal(token.text),
                            norm_start,
                            norm_end,
                        )
                    )
        elif kind is MatcherKind.PRICE_RANGE:
            sites.extend(
                _range_sites(
                    tuple(runtime.profile.range_patterns),
                    positioned,
                    win_start,
                    win_end,
                    disqualified,
                )
            )
        elif kind is MatcherKind.TOKEN_SEQUENCE:
            raw_categories_value = params.get("categories", ())
            raw_categories: tuple[object, ...] = (
                tuple(raw_categories_value)
                if isinstance(raw_categories_value, (list, tuple))
                else ()
            )
            categories_list: list[TokenCategory] = []
            for c in raw_categories:
                if isinstance(c, str):
                    categories_list.append(TokenCategory[c])
            categories = tuple(categories_list)
            sites.extend(_sequence_sites(categories, positioned, win_start, win_end))
    return sites


def _range_sites(
    range_patterns: tuple[str, ...],
    positioned: tuple[tuple[int, int, Token], ...],
    win_start: int,
    win_end: int,
    disqualified: frozenset[int],
) -> list[_Site]:
    sites: list[_Site] = []
    if not range_patterns:
        return sites
    for i in range(len(positioned) - 2):
        s1, _, tok1 = positioned[i]
        _, _, tok2 = positioned[i + 1]
        s3, e3, tok3 = positioned[i + 2]
        if not (win_start <= s1 and e3 <= win_end):
            continue
        if (
            tok1.category is TokenCategory.NUMBER
            and tok2.category is TokenCategory.PUNCT
            and tok2.text in range_patterns
            and tok3.category is TokenCategory.NUMBER
        ):
            # A range is exactly two numbers; either endpoint participating
            # in a longer numeric chain (e.g. a date "2026-09-05") or a
            # percent form disqualifies the range (§5.6 binding).
            if s1 in disqualified or s3 in disqualified:
                continue
            low, high = Decimal(tok1.text), Decimal(tok3.text)
            # §5.6 range invariant: a range is only valid when low <= high.
            # An inverted pair (e.g. "300/250") is never a valid executable
            # entry range — the site is rejected deterministically and the
            # endpoints stay preserved PRICE candidates (§7: no guessing of
            # direction-dependent ordering semantics).
            if low > high:
                continue
            value = PriceRange(low=Price(low), high=Price(high))
            sites.append(_Site(s1, e3, value, s1, e3))
    return sites


def _sequence_sites(
    categories: tuple[TokenCategory, ...],
    positioned: tuple[tuple[int, int, Token], ...],
    win_start: int,
    win_end: int,
) -> list[_Site]:
    if not categories:
        return []
    sites: list[_Site] = []
    content = [
        (s, e, t)
        for s, e, t in positioned
        if win_start <= s
        and e <= win_end
        and t.category is not TokenCategory.WHITESPACE
    ]
    for i in range(len(content) - len(categories) + 1):
        window_tokens = content[i : i + len(categories)]
        if all(t.category is cat for cat, (_, _, t) in zip(categories, window_tokens)):
            start = window_tokens[0][0]
            end = window_tokens[-1][1]
            value = tuple(t.text for _, _, t in window_tokens)
            sites.append(_Site(start, end, value, start, end))
    return sites


def _constraints_pass(
    rule: ProviderRule,
    params: dict[str, object],
    metadata: MessageMetadata,
    positioned: tuple[tuple[int, int, Token], ...],
) -> bool:
    keyword_texts = {
        token.text.lower()
        for _, _, token in positioned
        if token.category is TokenCategory.KEYWORD
    }
    raw_keywords_value = params.get("keywords", ())
    raw_keywords: tuple[object, ...] = (
        tuple(raw_keywords_value)
        if isinstance(raw_keywords_value, (list, tuple))
        else ()
    )
    required_forbidden: tuple[str, ...] = tuple(
        str(k) for k in raw_keywords if isinstance(k, str)
    )
    has_symbol = bool(params.get("requires_symbol")) and any(
        token.category is TokenCategory.SYMBOL for _, _, token in positioned
    )
    for constraint in rule.constraints:
        if constraint is Constraint.REQUIRES:
            has_any_keyword_req = bool(required_forbidden)
            has_symbol_req = bool(params.get("requires_symbol"))
            if not has_any_keyword_req and not has_symbol_req:
                continue
            if has_any_keyword_req and not any(
                k.lower() in keyword_texts for k in required_forbidden
            ):
                return False
            if has_symbol_req and not has_symbol:
                return False
        elif constraint is Constraint.FORBIDS:
            if any(k.lower() in keyword_texts for k in required_forbidden):
                return False
        elif (
            constraint is Constraint.REQUIRES_REPLY
            or constraint is Constraint.REQUIRES_CONTEXT
        ):
            if metadata.reply_to is None:
                return False
    return True


def _select_occurrences(
    rule: ProviderRule, params: dict[str, object], sites: list[_Site]
) -> list[_Site]:
    if rule.occurrence is OccurrenceSelection.FIRST:
        return sites[:1]
    if rule.occurrence is OccurrenceSelection.LAST:
        return sites[-1:]
    if rule.occurrence is OccurrenceSelection.NTH:
        raw_n = params.get("n", 1)
        n = int(raw_n) if isinstance(raw_n, (int, float)) else 1
        return [sites[n - 1]] if 0 < n <= len(sites) else []
    return sites


def _bind_candidate(
    rule: ProviderRule, site_value: object, raw_span: SourceSpan
) -> Candidate:
    candidate_slot = _SEMANTIC_TO_CANDIDATE_SLOT.get(rule.target.name)
    if candidate_slot is None:
        raise ValueError(
            f"rule {rule.id!r}: target {rule.target.name!r} has no CandidateSlot "
            "equivalent; cannot emit a candidate for it"
        )
    params = dict(rule.matcher.params)
    canonical_value = params.get("canonical")
    canonical_text: str | None = (
        str(canonical_value) if isinstance(canonical_value, str) else None
    )
    value: object = site_value
    provenance: tuple[MatchEvidence, ...] = (
        MatchEvidence(kind="rule_match", rule_id=rule.id, span=raw_span),
    )
    if candidate_slot is CandidateSlot.DIRECTION:
        text_for_enum = (
            canonical_text if canonical_text is not None else str(site_value)
        )
        # Keyword classification is case-insensitive (§5.4); enum lookups
        # must be too — "buy"/"Long" canonicalize to the enum name.
        value = TradeDirection[text_for_enum.upper()]
    elif candidate_slot is CandidateSlot.ENTRY_TRIGGER:
        text_for_enum = (
            canonical_text if canonical_text is not None else str(site_value)
        )
        value = EntryTrigger[text_for_enum.upper()]
    elif candidate_slot is CandidateSlot.ENTRY_GEOMETRY:
        text_for_enum = (
            canonical_text if canonical_text is not None else str(site_value)
        )
        value = EntryGeometry[text_for_enum.upper()]
    elif candidate_slot is CandidateSlot.ACTION:
        instruction = CATEGORY_INSTRUCTION.get(rule.category)
        if instruction is None:
            raise ValueError(
                f"rule {rule.id!r}: ACTION target with unknown category "
                f"{rule.category!r}; expected an action category"
            )
        value = instruction
        provenance = provenance + (
            MatchEvidence(
                kind="action_match",
                rule_id=rule.id,
                span=raw_span,
                snippet=str(site_value),
            ),
        )
    elif candidate_slot is CandidateSlot.CONDITION:
        # Design §8.2: a condition is a deterministic predicate, recorded but
        # never evaluated. The kind comes from the rule's declared
        # ``condition_kind`` matcher param (validated at profile load); the
        # operand shape is determined by the kind — AT_PRICE carries the
        # canonical price, KEYWORD_PRESENT the matched keyword text,
        # IN_PROFIT/NONE carry no operand.
        kind = ConditionKind[str(params.get("condition_kind"))]
        if kind is ConditionKind.AT_PRICE:
            if isinstance(site_value, Price):
                operand: object = site_value
            elif isinstance(site_value, Decimal):
                operand = Price(site_value)
            else:
                operand = Price(Decimal(str(site_value)))
            condition_params: tuple[tuple[str, object], ...] = (("price", operand),)
        elif kind is ConditionKind.KEYWORD_PRESENT:
            condition_params = (("keyword", str(site_value)),)
        else:
            condition_params = ()
        value = Condition(kind=kind, params=condition_params)
    elif candidate_slot in (CandidateSlot.ENTRY, CandidateSlot.SL, CandidateSlot.TP):
        if isinstance(site_value, (Price, PriceRange)):
            value = site_value
        elif isinstance(site_value, Decimal):
            value = Price(site_value)
        else:
            value = Price(Decimal(str(site_value)))
    if canonical_text is not None and candidate_slot is not CandidateSlot.ACTION:
        provenance = provenance + (
            MatchEvidence(
                kind="canonical_alias",
                rule_id=rule.id,
                span=raw_span,
                fields=(("raw", str(site_value)), ("canonical", canonical_text)),
            ),
        )
    return Candidate(
        slot=candidate_slot,
        value=value,
        source_span=raw_span,
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# Resolution (§6.2) — classification of competing candidates
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Resolution:
    """Post-resolution semantic candidates (§6.2, §13.1)."""

    winners: tuple[Candidate, ...] = ()
    entry_values: tuple[Price | PriceRange, ...] = ()
    tp_values: tuple[Price, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    ambiguities: tuple[Ambiguity, ...] = ()


def resolve_candidates(
    matches: tuple[RuleMatch, ...],
    graph: CandidateGraph | None,
    runtime: ProfileRuntime,
) -> _Resolution:
    """Classify competing candidates per §6.2 (deterministic order §6.3).

    The CandidateGraph is the authoritative intermediate representation of
    candidate alternatives (§5.7, §6.1): the resolver merges the rule-bound
    candidates with the graph's per-slot alternatives (non-selected
    occurrence sites) and pre-rule keyword candidates, so conflicting
    candidates survive until resolution instead of being silently
    discarded because they appeared second.

    - duplicates (same slot/value/span) collapse with merged provenance;
    - §7.3 overlap precedence: when two candidates for the same slot have
      overlapping precedence spans (the RULE match span for rule-bound
      candidates, the candidate span otherwise), the longer span wins;
      equal length → lower ``priority``; equal priority → lexicographic
      ``rule_id``. Suppressed candidates are dropped from the winners list
      (not classified as conflicts). This is the §7.3 rule-evaluation
      ordering applied at resolution time.
    - differing values in a conflict slot emit a Conflict;
    - differing ENTRY_TRIGGER values emit AMBIGUOUS_TRIGGER;
    - TP (and REPEATABLE-bound ENTRY rules) accumulate multi-values;
    - otherwise the FIRST candidate (§6.3 order) is the winner; conflicts
      are recorded alongside so nothing is silently chosen.
    """
    rule_index: dict[str, ProviderRule] = {
        rule.id: rule for rule in runtime.effective_rules
    }
    repeatable_ids = {
        r.id for r in runtime.effective_rules if Constraint.REPEATABLE in r.constraints
    }

    # Merge rule-bound candidates with the CandidateGraph alternatives.
    # Reference slots (PRICE/RANGE) stay outside semantic resolution.
    entries: list[tuple[Candidate, SourceSpan]] = []
    for rule_match in matches:
        for _, candidate in rule_match.bindings:
            entries.append((candidate, rule_match.span))
    for slot, graph_candidates in graph.by_slot if graph else ():
        if slot in (CandidateSlot.PRICE, CandidateSlot.RANGE):
            continue
        entries.extend(
            (candidate, candidate.source_span) for candidate in graph_candidates
        )
    entries.sort(key=lambda pair: _candidate_order(pair[0]))

    conflicts: list[Conflict] = []
    ambiguities: list[Ambiguity] = []
    tp_values: list[Price] = []
    entry_values: list[Price | PriceRange] = []
    winners: list[Candidate] = []

    for slot in CandidateSlot:
        slot_entries = [pair for pair in entries if pair[0].slot is slot]
        if not slot_entries:
            continue
        deduped = _dedupe_entries(slot_entries)
        survivors = _suppress_overlaps(deduped, rule_index)
        if not survivors:
            continue
        candidates = [candidate for candidate, _prec in survivors]
        if slot is CandidateSlot.TP:
            for candidate in candidates:
                if (
                    isinstance(candidate.value, Price)
                    and candidate.value not in tp_values
                ):
                    tp_values.append(candidate.value)
            winners.append(candidates[0])
            continue
        distinct: list[Candidate] = []
        for candidate in candidates:
            if not any(c.value == candidate.value for c in distinct):
                distinct.append(candidate)
        if len(distinct) == 1:
            winners.append(candidates[0])
            if slot is CandidateSlot.ENTRY:
                value = distinct[0].value
                if isinstance(value, (Price, PriceRange)):
                    entry_values.append(value)
            continue
        if slot is CandidateSlot.ENTRY and all(
            any(
                e.rule_id in repeatable_ids
                for e in candidate.provenance
                if e.rule_id is not None
            )
            for candidate in distinct
        ):
            for candidate in distinct:
                if isinstance(candidate.value, (Price, PriceRange)):
                    entry_values.append(candidate.value)
            winners.append(distinct[0])
            continue
        if slot is CandidateSlot.ENTRY_TRIGGER:
            ambiguities.append(
                Ambiguity(
                    kind=AmbiguityKind.AMBIGUOUS_TRIGGER,
                    slot=slot,
                    candidates=tuple(distinct),
                    spans=tuple(c.source_span for c in distinct),
                    reason="multiple valid trigger interpretations",
                )
            )
            continue
        if slot in _CONFLICT_SLOTS:
            conflicts.append(
                Conflict(
                    kind=ConflictKind.CONFLICTING,
                    slot=slot,
                    involved=tuple(distinct),
                    spans=tuple(c.source_span for c in distinct),
                    reason=f"conflicting values for slot {slot.name}",
                )
            )
            winners.append(distinct[0])
        # PRICE / RANGE reference candidates are not rule-bound here.
    return _Resolution(
        winners=tuple(winners),
        entry_values=tuple(entry_values),
        tp_values=tuple(tp_values),
        conflicts=tuple(conflicts),
        ambiguities=tuple(ambiguities),
    )


def _dedupe_entries(
    entries: list[tuple[Candidate, SourceSpan]],
) -> list[tuple[Candidate, SourceSpan]]:
    """Collapse duplicate candidates (same slot, value, span) merging both
    provenance and keeping the first precedence span (§6.2 duplicate)."""
    deduped: list[tuple[Candidate, SourceSpan]] = []
    for candidate, prec in entries:
        merged = False
        for i, (kept, kept_prec) in enumerate(deduped):
            if (
                kept.value == candidate.value
                and kept.source_span == candidate.source_span
            ):
                deduped[i] = (
                    Candidate(
                        slot=kept.slot,
                        value=kept.value,
                        source_span=kept.source_span,
                        provenance=kept.provenance + candidate.provenance,
                    ),
                    kept_prec,
                )
                merged = True
                break
        if not merged:
            deduped.append((candidate, prec))
    return deduped


def _suppress_overlaps(
    entries: list[tuple[Candidate, SourceSpan]], rule_index: dict[str, ProviderRule]
) -> list[tuple[Candidate, SourceSpan]]:
    """Apply §7.3 overlap precedence: among candidates for the same slot,
    longer PRECEDENCE span wins; equal length → lower priority; equal
    priority → lexicographic rule_id. Subordinate candidates are dropped.
    """
    kept: list[tuple[Candidate, SourceSpan]] = []
    for candidate, prec in entries:
        drop = False
        kept_copy = list(kept)
        for other, other_prec in kept_copy:
            if _spans_overlap(prec, other_prec):
                loser = _select_overlap_loser(
                    candidate, other, prec, other_prec, rule_index
                )
                if loser is candidate:
                    drop = True
                    break
                if loser is other:
                    kept.remove((other, other_prec))
        if not drop:
            kept.append((candidate, prec))
    return kept


def _spans_overlap(a: SourceSpan, b: SourceSpan) -> bool:
    return not (a.end <= b.start or b.end <= a.start)


def _select_overlap_loser(
    a: Candidate,
    b: Candidate,
    a_prec: SourceSpan,
    b_prec: SourceSpan,
    rule_index: dict[str, ProviderRule],
) -> Candidate:
    """Return the candidate to drop under §7.3 overlap precedence."""
    a_len = a_prec.end - a_prec.start
    b_len = b_prec.end - b_prec.start
    if a_len != b_len:
        return a if a_len < b_len else b
    a_rule = _rule_for_candidate(a, rule_index)
    b_rule = _rule_for_candidate(b, rule_index)
    if a_rule is not None and b_rule is not None:
        if a_rule.priority != b_rule.priority:
            return a if a_rule.priority > b_rule.priority else b
        if a_rule.id != b_rule.id:
            return a if a_rule.id > b_rule.id else b
    if a_prec.start != b_prec.start:
        return a if a_prec.start > b_prec.start else b
    return a if a_prec.end > b_prec.end else b


def _rule_for_candidate(
    candidate: Candidate, rule_index: dict[str, ProviderRule]
) -> ProviderRule | None:
    for evidence in candidate.provenance:
        if evidence.rule_id is not None and evidence.rule_id in rule_index:
            return rule_index[evidence.rule_id]
    return None


def _rule_index_for(runtime: ProfileRuntime) -> dict[str, ProviderRule]:
    return {rule.id: rule for rule in runtime.effective_rules}


# ---------------------------------------------------------------------------
# Fragments, outcome, IR (§5.12, §14, §13)
# ---------------------------------------------------------------------------


def _fragments_from_winners(
    resolution: _Resolution,
    rule_flags: dict[str, tuple[tuple[str, object], ...]],
    rule_index: dict[str, ProviderRule],
) -> tuple[ParsedFragment, ...]:
    """Emit ParsedFragments from resolved winners.

    When an ACTION candidate is present, signal-context fragments
    (ENTRY, SL, TP) are suppressed UNLESS their binding rule explicitly
    tolerates being inside an action context — i.e., the rule declares
    ``REQUIRES`` with a direction keyword (BUY/SELL/LONG/SHORT) in its
    ``keywords`` param. This prevents a number like ``50`` inside
    ``"CLOSE 50%"`` from being emitted as ENTRY=50 alongside ACTION=
    PARTIAL_CLOSE. The suppressed candidates are still preserved in the
    ``CanonicalParserIR.candidates`` field for evidence.
    """
    fragments: list[ParsedFragment] = []
    ambiguous_slots = {a.slot for a in resolution.ambiguities}
    action_present = any(c.slot is CandidateSlot.ACTION for c in resolution.winners)

    def _is_signal_context_rule(rule: ProviderRule | None) -> bool:
        if rule is None:
            return False
        params = dict(rule.matcher.params)
        raw_declared_value = params.get("keywords", ())
        raw_declared: tuple[object, ...] = (
            tuple(raw_declared_value)
            if isinstance(raw_declared_value, (list, tuple))
            else ()
        )
        declared_keywords = tuple(str(k) for k in raw_declared if isinstance(k, str))
        if not declared_keywords:
            return False
        direction_words = {"BUY", "SELL", "LONG", "SHORT"}
        return any(k.upper() in direction_words for k in declared_keywords)

    def _should_suppress_signal_slot(candidate: Candidate) -> bool:
        if not action_present:
            return False
        if candidate.slot not in (
            CandidateSlot.ENTRY,
            CandidateSlot.SL,
            CandidateSlot.TP,
        ):
            return False
        rule_id = next(
            (e.rule_id for e in candidate.provenance if e.rule_id is not None),
            None,
        )
        rule = rule_index.get(rule_id) if rule_id is not None else None
        return not _is_signal_context_rule(rule)

    for candidate in resolution.winners:
        if _should_suppress_signal_slot(candidate):
            continue
        if candidate.slot is CandidateSlot.TP:
            fragments.append(
                ParsedFragment(
                    slot=CandidateSlot.TP,
                    value=resolution.tp_values,
                    state=FragmentState.RESOLVED,
                    evidence=candidate.provenance,
                )
            )
            continue
        if candidate.slot is CandidateSlot.ENTRY and len(resolution.entry_values) > 1:
            fragments.append(
                ParsedFragment(
                    slot=CandidateSlot.ENTRY,
                    value=resolution.entry_values,
                    state=FragmentState.RESOLVED,
                    evidence=candidate.provenance,
                )
            )
            continue
        if candidate.slot is CandidateSlot.ENTRY_TRIGGER and (
            candidate.slot in ambiguous_slots
        ):
            continue
        context = (
            ContextRequirement.LAST_SIGNAL
            if candidate.slot is CandidateSlot.ACTION
            else ContextRequirement.NONE
        )
        rule_id = next(
            (e.rule_id for e in candidate.provenance if e.rule_id is not None), None
        )
        extra_evidence: tuple[MatchEvidence, ...] = ()
        flags = rule_flags.get(rule_id or "", ())
        if flags:
            extra_evidence = (
                MatchEvidence(kind="action_flags", rule_id=rule_id, fields=flags),
            )
        fragments.append(
            ParsedFragment(
                slot=candidate.slot,
                value=candidate.value,
                state=FragmentState.RESOLVED,
                evidence=candidate.provenance + extra_evidence,
                context_requirement=context,
            )
        )
    return tuple(fragments)


def _derive_geometry(
    resolution: _Resolution, rule_index: dict[str, ProviderRule]
) -> EntryGeometry | None:
    action_present = any(c.slot is CandidateSlot.ACTION for c in resolution.winners)

    def _signal_context_values() -> tuple[Price | PriceRange, ...]:
        if not action_present:
            return resolution.entry_values
        kept: list[Price | PriceRange] = []
        for value, candidate in zip(
            resolution.entry_values,
            (c for c in resolution.winners if c.slot is CandidateSlot.ENTRY),
        ):
            rule_id = next(
                (e.rule_id for e in candidate.provenance if e.rule_id is not None),
                None,
            )
            rule = rule_index.get(rule_id) if rule_id is not None else None
            params = dict(rule.matcher.params) if rule is not None else {}
            declared_keywords_value = params.get("keywords", ())
            declared_keywords_iter: tuple[object, ...] = (
                tuple(declared_keywords_value)
                if isinstance(declared_keywords_value, (list, tuple))
                else ()
            )
            declared_keywords = tuple(
                str(k) for k in declared_keywords_iter if isinstance(k, str)
            )
            direction_words = {"BUY", "SELL", "LONG", "SHORT"}
            if rule is not None and any(
                k.upper() in direction_words for k in declared_keywords
            ):
                kept.append(value)
        return tuple(kept)

    for candidate in resolution.winners:
        if (
            candidate.slot is CandidateSlot.ENTRY_TRIGGER
            and candidate.value is EntryTrigger.MARKET
        ):
            return EntryGeometry.MARKET
    effective_entry_values = _signal_context_values()
    if any(isinstance(v, PriceRange) for v in effective_entry_values):
        return EntryGeometry.RANGE
    if len(effective_entry_values) > 1:
        return EntryGeometry.MULTIPLE
    if len(effective_entry_values) == 1:
        return EntryGeometry.SINGLE
    return None


def _unit_core(
    raw: RawMessage,
    metadata: MessageMetadata,
    runtime: ProfileRuntime,
    normalized: NormalizedMessage,
    graph: CandidateGraph | None,
    matches: tuple[RuleMatch, ...],
    violations: tuple[_Violation, ...],
    unsupported: tuple[_Violation, ...],
    rule_flags: dict[str, tuple[tuple[str, object], ...]],
) -> ParseResult:
    """Resolve + classify ONE evaluation unit (whole message or block).

    This is the §14.1/§14.2 outcome decision procedure plus §6.2 candidate
    resolution, extracted verbatim from the former single-unit body of
    :func:`build_parse_result` so that whole-message and per-block
    evaluation share exactly one deterministic code path (ADR 0013).
    """
    profile = runtime.profile
    evidence: list[MatchEvidence] = []
    conflicts: tuple[Conflict, ...] = ()
    ambiguities: tuple[Ambiguity, ...] = ()
    candidates: tuple[Candidate, ...] = ()
    fragments: tuple[ParsedFragment, ...] = ()
    unresolved: list[CandidateSlot] = []
    conditions: tuple[Condition, ...] = ()
    normalization_decisions = normalized.normalization_decisions
    correlation: CorrelationRequest | None = None
    context_ref: ContextReference | None = metadata.reply_to

    if raw.media_refs and MediaKind.NONE not in raw.media_refs:
        evidence.append(
            MatchEvidence(kind="media_present", reason="media recorded, never opened")
        )

    # --- structural violations (§15.3 bounds) ------------------------------
    blocking = [v for v in violations if v.kind != "grammar_violation_missing_number"]
    if blocking:
        for v in blocking:
            evidence.append(
                MatchEvidence(kind=v.kind, rule_id=v.rule_id, reason=v.detail)
            )
        return _finalize(
            ParseResultState.MALFORMED,
            metadata,
            evidence,
            normalization_decisions,
            candidates,
            unresolved,
            fragments,
            conflicts,
            ambiguities,
            conditions,
            context_ref,
            correlation,
        )

    # --- candidate resolution (§6.2) ---------------------------------------
    resolved = resolve_candidates(matches, graph, runtime)
    conflicts = resolved.conflicts
    ambiguities = resolved.ambiguities
    candidates = resolved.winners + tuple(
        candidate
        for slot, slot_candidates in (graph.by_slot if graph else ())
        for candidate in slot_candidates
        if slot in (CandidateSlot.PRICE, CandidateSlot.RANGE)
    )
    for candidate in resolved.winners:
        if candidate.slot is CandidateSlot.CONDITION and isinstance(
            candidate.value, Condition
        ):
            conditions = conditions + (candidate.value,)
    fragments = _fragments_from_winners(resolved, rule_flags, _rule_index_for(runtime))

    direction = _winner_value(resolved, CandidateSlot.DIRECTION)
    instrument = _winner_value(resolved, CandidateSlot.INSTRUMENT)
    action = _winner_value(resolved, CandidateSlot.ACTION)
    geometry = _derive_geometry(resolved, _rule_index_for(runtime))
    if geometry is not None:
        fragments = fragments + (
            ParsedFragment(
                slot=CandidateSlot.ENTRY_GEOMETRY,
                value=geometry,
                state=FragmentState.RESOLVED,
            ),
        )

    grammar_violations = [
        v for v in violations if v.kind == "grammar_violation_missing_number"
    ]

    # --- outcome decision procedure (§14.1, §14.2) --------------------------
    if grammar_violations:
        outcome = ParseResultState.MALFORMED
        for v in grammar_violations:
            evidence.append(
                MatchEvidence(
                    kind="grammar_violation_missing_number",
                    rule_id=v.rule_id,
                    reason=v.detail,
                )
            )
    elif conflicts:
        outcome = ParseResultState.MALFORMED
        evidence.append(MatchEvidence(kind="conflicting_candidates"))
    elif unsupported and direction is None and action is None:
        outcome = ParseResultState.UNSUPPORTED
        for u in unsupported:
            evidence.append(
                MatchEvidence(
                    kind="unsupported_feature", rule_id=u.rule_id, reason=u.detail
                )
            )
    elif ambiguities:
        outcome = ParseResultState.AMBIGUOUS
        evidence.append(MatchEvidence(kind="ambiguous_interpretation"))
    elif action is not None:
        if (
            action is InstructionType.MOVE_SL
            and instrument is None
            and not resolved.entry_values
        ):
            evidence.append(MatchEvidence(kind="follow_up_only"))
            outcome = ParseResultState.NO_SIGNAL
            if profile.follow_up_behavior.name == "TARGET_LAST_SIGNAL":
                correlation = CorrelationRequest(
                    kind=CorrelationRequestKind.TARGET_LAST_SIGNAL,
                    target=ContextReference(
                        provider_name=metadata.provider_name,
                        kind=ContextReferenceKind.LAST_SIGNAL,
                    ),
                    fragments=fragments,
                )
        else:
            outcome = ParseResultState.PARSED
            if profile.capabilities.last_signal_execution:
                correlation = CorrelationRequest(
                    kind=CorrelationRequestKind.TARGET_LAST_SIGNAL,
                    target=ContextReference(
                        provider_name=metadata.provider_name,
                        kind=ContextReferenceKind.LAST_SIGNAL,
                    ),
                    fragments=fragments,
                )
    elif direction is not None:
        has_entry = bool(resolved.entry_values) or geometry is EntryGeometry.MARKET
        if not has_entry:
            if profile.capabilities.multi_message:
                evidence.append(MatchEvidence(kind="entry_pending"))
                unresolved = [
                    CandidateSlot.ENTRY,
                    CandidateSlot.ENTRY_GEOMETRY,
                    CandidateSlot.ENTRY_TRIGGER,
                ]
                fragments = fragments + tuple(
                    ParsedFragment(
                        slot=slot,
                        value=None,
                        state=FragmentState.UNRESOLVED,
                        evidence=(MatchEvidence(kind="entry_pending"),),
                    )
                    for slot in unresolved
                )
                outcome = ParseResultState.PARTIAL
            else:
                outcome = ParseResultState.MALFORMED
                evidence.append(MatchEvidence(kind="grammar_violation_missing_number"))
        else:
            outcome = ParseResultState.PARSED
    else:
        evidence.append(MatchEvidence(kind="no_signal_content"))
        outcome = ParseResultState.NO_SIGNAL

    if metadata.message_event is MessageEvent.EDIT:
        context_ref = (
            ContextReference(
                provider_name=metadata.provider_name,
                kind=ContextReferenceKind.EDITED_ORIGINAL,
            )
            if context_ref is None
            else context_ref
        )
        correlation = CorrelationRequest(
            kind=CorrelationRequestKind.EDIT_APPLY, target=context_ref
        )

    return _finalize(
        outcome,
        metadata,
        evidence,
        normalization_decisions,
        candidates,
        unresolved,
        fragments,
        conflicts,
        ambiguities,
        conditions,
        context_ref,
        correlation,
    )


def build_parse_result(
    raw: RawMessage,
    metadata: MessageMetadata,
    runtime: ProfileRuntime,
    norm_reject_code: str | None,
    normalized: NormalizedMessage | None,
    graph: CandidateGraph | None,
    matches: tuple[RuleMatch, ...],
    violations: tuple[_Violation, ...],
    unsupported: tuple[_Violation, ...],
    rule_flags: dict[str, tuple[tuple[str, object], ...]],
) -> ParseResult:
    profile = runtime.profile
    evidence: list[MatchEvidence] = []
    normalization_decisions: tuple[str, ...] = ()
    correlation: CorrelationRequest | None = None
    context_ref: ContextReference | None = metadata.reply_to

    # --- stage-level pre-semantic decisions (§14) -------------------------
    if norm_reject_code in (
        "message_too_long",
        "embedded_control_char",
        "zero_width_only",
        "bidi_control_only",
    ):
        evidence.append(MatchEvidence(kind=norm_reject_code))
        return _finalize(
            ParseResultState.MALFORMED,
            metadata,
            evidence,
            normalization_decisions,
            (),
            [],
            (),
            (),
            (),
            (),
            context_ref,
            correlation,
        )
    if norm_reject_code == "empty_after_normalization" or raw.raw_text.strip() == "":
        if raw.media_refs and MediaKind.NONE not in raw.media_refs:
            evidence.append(MatchEvidence(kind="media_only_unopened"))
            outcome = ParseResultState.UNSUPPORTED
        else:
            evidence.append(MatchEvidence(kind="empty_message"))
            outcome = ParseResultState.NO_SIGNAL
        return _finalize(
            outcome,
            metadata,
            evidence,
            normalization_decisions,
            (),
            [],
            (),
            (),
            (),
            (),
            context_ref,
            correlation,
        )

    if metadata.message_event is MessageEvent.DELETE:
        evidence.append(MatchEvidence(kind="message_deleted"))
        if profile.delete_behavior.name == "CANCEL_TARGET":
            correlation = CorrelationRequest(kind=CorrelationRequestKind.DELETE_APPLY)
        return _finalize(
            ParseResultState.NO_SIGNAL,
            metadata,
            evidence,
            normalization_decisions,
            (),
            [],
            (),
            (),
            (),
            (),
            context_ref,
            correlation,
        )

    if (
        metadata.message_event is MessageEvent.EDIT
        and profile.edit_behavior.name == "IGNORE"
    ):
        evidence.append(MatchEvidence(kind="edit_ignored"))
        return _finalize(
            ParseResultState.NO_SIGNAL,
            metadata,
            evidence,
            normalization_decisions,
            (),
            [],
            (),
            (),
            (),
            (),
            context_ref,
            correlation,
        )

    assert normalized is not None
    return _unit_core(
        raw,
        metadata,
        runtime,
        normalized,
        graph,
        matches,
        violations,
        unsupported,
        rule_flags,
    )


def _winner_value(resolution: _Resolution, slot: CandidateSlot) -> object | None:
    for candidate in resolution.winners:
        if candidate.slot is slot:
            return candidate.value
    return None


def _finalize(
    outcome: ParseResultState,
    metadata: MessageMetadata,
    evidence: list[MatchEvidence],
    normalization_decisions: tuple[str, ...],
    candidates: tuple[Candidate, ...],
    unresolved: list[CandidateSlot],
    fragments: tuple[ParsedFragment, ...],
    conflicts: tuple[Conflict, ...],
    ambiguities: tuple[Ambiguity, ...],
    conditions: tuple[Condition, ...],
    context_ref: ContextReference | None,
    correlation: CorrelationRequest | None,
) -> ParseResult:
    ir = CanonicalParserIR(
        candidates=candidates,
        unresolved_fields=tuple(unresolved),
        fragments=fragments,
        conflicts=conflicts,
        ambiguities=ambiguities,
        evidence=tuple(evidence),
        normalization_decisions=normalization_decisions,
        conditions=conditions,
        provider_id=metadata.provider_name,
        parser_version=PARSER_VERSION,
        context_reference=context_ref,
        correlation_request=correlation,
        source_ref=metadata.source_reference,
    )
    return ParseResult(outcome=outcome, ir=ir)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def parse(
    raw: RawMessage, metadata: MessageMetadata, runtime: ProfileRuntime
) -> ParseResult:
    """Run the full pipeline (§4.6). Pure; no I/O; no clock."""
    if metadata.provider_name != runtime.profile.provider_name:
        raise ValueError(
            f"provider_mismatch: metadata {metadata.provider_name!r} vs profile "
            f"{runtime.profile.provider_name!r}"
        )
    norm_reject_code: str | None = None
    normalized: NormalizedMessage | None = None
    graph: CandidateGraph | None = None
    matches: tuple[RuleMatch, ...] = ()
    violations: tuple[_Violation, ...] = ()
    unsupported: tuple[_Violation, ...] = ()
    if not (
        metadata.message_event is MessageEvent.DELETE
        or (
            metadata.message_event is MessageEvent.EDIT
            and runtime.profile.edit_behavior.name == "IGNORE"
        )
    ):
        try:
            normalized = normalize(raw.raw_text, runtime)
        except _NormalizationRejected as rejected:
            norm_reject_code = rejected.code
            normalized = None
        if normalized is not None:
            positioned, tokenize_violations = tokenize(normalized, runtime)
            blocks = _segment_blocks(normalized, positioned, raw.raw_text, runtime)
            if blocks is not None:
                return _parse_sectioned(
                    raw,
                    metadata,
                    runtime,
                    normalized,
                    positioned,
                    tokenize_violations,
                    blocks,
                )
            extract_graph, _, extract_violations = extract_candidates(
                positioned, runtime
            )
            (
                rule_matches,
                rule_violations,
                unsupported,
                site_candidates,
            ) = evaluate_rules(positioned, normalized, metadata, runtime, raw.raw_text)
            matches = rule_matches
            violations = tokenize_violations + extract_violations + rule_violations
            # The CandidateGraph is the authoritative pre-resolution
            # candidate store (§5.7, §6.1): pre-rule token candidates and
            # ALL rule-site candidates merge into one graph so competing
            # candidates survive until semantic resolution.
            graph = _merge_candidate_graphs(extract_graph, site_candidates)

    return build_parse_result(
        raw,
        metadata,
        runtime,
        norm_reject_code,
        normalized,
        graph,
        matches,
        violations,
        unsupported,
        _collect_rule_flags(runtime),
    )


def _collect_rule_flags(
    runtime: ProfileRuntime,
) -> dict[str, tuple[tuple[str, object], ...]]:
    """Per-rule action flags (design §20.10-§20.12): ``remove_sl``,
    ``cancel_pending``, ``trigger_pending`` — the payloads that distinguish
    REMOVE SL from a generic MOVE_SL, and TRIGGER PENDING from a generic
    MODIFY. Flags come from the rule's category (mapped via
    CATEGORY_CAPABILITY) and from an explicitly declared ``flags`` matcher
    param (declared entries first, category-derived entries appended)."""
    flags: dict[str, tuple[tuple[str, object], ...]] = {}
    for rule in runtime.effective_rules:
        entries: list[tuple[str, object]] = []
        params = dict(rule.matcher.params)
        raw_flags = params.get("flags")
        if isinstance(raw_flags, dict):
            entries.extend((str(k), v) for k, v in raw_flags.items())
        elif isinstance(raw_flags, (list, tuple)):
            entries.extend((str(k), v) for k, v in raw_flags)
        capability = CATEGORY_CAPABILITY.get(rule.category)
        if capability is not None:
            entries.append((capability, True))
        if entries:
            flags[rule.id] = tuple(entries)
    return flags


def _merge_candidate_graphs(
    base: CandidateGraph, alternatives: tuple[Candidate, ...]
) -> CandidateGraph:
    """Merge pre-rule candidates with rule-site alternatives into one
    deterministic CandidateGraph (§5.7 ordering)."""
    by_slot: dict[CandidateSlot, list[Candidate]] = {}
    for slot, candidates in base.by_slot:
        by_slot.setdefault(slot, []).extend(candidates)
    for candidate in alternatives:
        by_slot.setdefault(candidate.slot, []).append(candidate)
    entries = tuple(
        (slot, tuple(sorted(candidates, key=_candidate_order)))
        for slot, candidates in sorted(by_slot.items(), key=lambda kv: kv[0].name)
    )
    return CandidateGraph(by_slot=entries)


# ---------------------------------------------------------------------------
# Multi-block segmentation + aggregation (ADR 0013)
# ---------------------------------------------------------------------------


# Payload-fingerprint slots (ADR 0013 §6): the semantic identity of one
# block. Geometry is derived from entry and is excluded; comparison is
# equality-based (no hashing), so fingerprint tuples stay fully inspectable.
_FINGERPRINT_SLOTS: frozenset[CandidateSlot] = frozenset(
    {
        CandidateSlot.DIRECTION,
        CandidateSlot.INSTRUMENT,
        CandidateSlot.ENTRY_TRIGGER,
        CandidateSlot.ENTRY,
        CandidateSlot.SL,
        CandidateSlot.TP,
        CandidateSlot.ACTION,
    }
)


def _find_divider_spans(text: str, dividers: tuple[str, ...]) -> list[tuple[int, int]]:
    """All divider occurrences in normalized text, left to right,
    longest-first at each position (deterministic; dividers never
    overlap)."""
    spans: list[tuple[int, int]] = []
    ordered = sorted(dividers, key=len, reverse=True)
    i = 0
    while i < len(text):
        for divider in ordered:
            if text.startswith(divider, i):
                spans.append((i, i + len(divider)))
                i += len(divider)
                break
        else:
            i += 1
    return spans


def _trim_whitespace(
    start: int,
    end: int,
    ws_by_start: dict[int, int],
    ws_by_end: dict[int, int],
) -> tuple[int, int]:
    """Strip whitespace tokens from the edges of a candidate block span.

    Edge walk over precomputed whitespace-span maps (O(1) per step) so
    segmentation stays linear in the number of whitespace tokens even for
    pathological section counts (Phase 2F adversarial audit)."""
    while True:
        nxt = ws_by_start.get(start)
        if nxt is not None and nxt < end:
            start = nxt
            continue
        prv = ws_by_end.get(end)
        if prv is not None and prv > start:
            end = prv
            continue
        return start, end


def _segment_blocks(
    normalized: NormalizedMessage,
    positioned: tuple[tuple[int, int, Token], ...],
    raw_text: str,
    runtime: ProfileRuntime,
) -> tuple[MessageBlock, ...] | None:
    """Mechanically segment a SECTIONED message into blocks (ADR 0013).

    Strong boundaries are profile-declared dividers (e.g. ``⸻``), matched
    on the normalized text. Weak boundaries are blank-line whitespace runs
    (raw chunk containing two or more line terminators) and are active
    ONLY in sectioned messages — ordinary signals are full of blank lines
    and must never be split (ADR 0013 audit). Single newlines are
    ordinary intra-block whitespace.

    Returns None when the message is one unit (no dividers declared, no
    divider present, or fewer than two non-empty blocks) — the caller
    then uses the legacy whole-message path byte-identically. The
    separator characters (dividers, blank-line runs) belong to no block;
    blocks carry global normalized and raw bounds (SourceMap is never
    re-based).
    """
    dividers = tuple(runtime.profile.section_dividers)
    if not dividers:
        return None
    text = normalized.normalized_text
    smap = normalized.source_map
    boundaries: list[tuple[int, int, BlockSeparatorKind]] = [
        (start, end, BlockSeparatorKind.DIVIDER)
        for start, end in _find_divider_spans(text, dividers)
    ]
    if not boundaries:
        return None
    for norm_start, norm_end, tok in positioned:
        if tok.category is not TokenCategory.WHITESPACE:
            continue
        raw_start, raw_end = smap.char_ranges[norm_start]
        chunk = raw_text[raw_start:raw_end]
        if chunk.count("\n") + chunk.count("\r") >= 2:
            boundaries.append((norm_start, norm_end, BlockSeparatorKind.BLANK_LINE))
    boundaries.sort(key=lambda b: (b[0], b[1]))

    gaps: list[tuple[int, int, BlockSeparatorKind]] = []
    cursor = 0
    cursor_kind = BlockSeparatorKind.NONE
    for b_start, b_end, kind in boundaries:
        if cursor < b_start:
            gaps.append((cursor, b_start, cursor_kind))
        cursor = b_end
        cursor_kind = kind
    if cursor < len(text):
        gaps.append((cursor, len(text), cursor_kind))

    ws_by_start = {
        s: e for s, e, tok in positioned if tok.category is TokenCategory.WHITESPACE
    }
    ws_by_end = {
        e: s for s, e, tok in positioned if tok.category is TokenCategory.WHITESPACE
    }
    content_starts = [
        s for s, _, tok in positioned if tok.category is not TokenCategory.WHITESPACE
    ]
    blocks: list[MessageBlock] = []
    for gap_start, gap_end, kind in gaps:
        start, end = _trim_whitespace(gap_start, gap_end, ws_by_start, ws_by_end)
        if start >= end:
            continue
        idx = bisect_left(content_starts, start)
        has_content = idx < len(content_starts) and content_starts[idx] < end
        if not has_content:
            continue
        raw_start, raw_end = smap.raw_span_for(start, end)
        blocks.append(
            MessageBlock(
                index=len(blocks),
                norm_start=start,
                norm_end=end,
                raw_start=raw_start,
                raw_end=raw_end,
                separator_kind=kind,
            )
        )
    if len(blocks) <= 1:
        return None
    return tuple(blocks)


def _clip_line_windows_all(
    line_windows: tuple[tuple[int, int], ...],
    blocks: tuple[MessageBlock, ...],
) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Clip full-message LINE windows to every block in one sweep.

    Blocks and line windows are both sorted ascending, so a two-pointer
    pass distributes each window to the blocks it overlaps (O(L + B))
    instead of rescanning all windows per block (Phase 2F audit)."""
    clipped: list[list[tuple[int, int]]] = [[] for _ in blocks]
    window_index = 0
    for block in blocks:
        while (
            window_index < len(line_windows)
            and line_windows[window_index][1] <= block.norm_start
        ):
            window_index += 1
        scan = window_index
        while scan < len(line_windows) and line_windows[scan][0] < block.norm_end:
            start = max(line_windows[scan][0], block.norm_start)
            end = min(line_windows[scan][1], block.norm_end)
            if start < end:
                clipped[block.index].append((start, end))
            scan += 1
    return tuple(tuple(windows) for windows in clipped)


def _block_fingerprint(
    ir: CanonicalParserIR,
) -> tuple[tuple[object, object], ...] | None:
    """Structured payload fingerprint of one block (ADR 0013 §6).

    Comparison-only (tuple equality): distinguishes duplicated provider
    feed copies from genuinely distinct signals; the parser never
    collapses or executes on it (correlation is Phase 3+)."""
    items: list[tuple[object, object]] = []
    for fragment in ir.fragments:
        if (
            fragment.slot in _FINGERPRINT_SLOTS
            and fragment.state is FragmentState.RESOLVED
            and fragment.value is not None
        ):
            items.append((fragment.slot, fragment.value))
    return tuple(items) or None


def _aggregate_ir(
    metadata: MessageMetadata,
    normalized: NormalizedMessage,
    unit_results: list[tuple[MessageBlock, ParseResultState, CanonicalParserIR]],
    outcome: ParseResultState,
    source_block: MessageBlock | None,
) -> CanonicalParserIR:
    """Top-level aggregate IR for a multi-block message (ADR 0013 §5).

    Deliberately fragment-free: consumers MUST read ``blocks``. Evidence
    records the aggregation and, on escalation, the deterministic source
    block of the message outcome."""
    evidence: list[MatchEvidence] = [
        MatchEvidence(
            kind="multi_block_message", fields=(("blocks", len(unit_results)),)
        ),
    ]
    if outcome is ParseResultState.MULTI_SIGNAL:
        evidence.append(
            MatchEvidence(
                kind="multi_signal",
                reason=(
                    "multiple executable blocks; top-level IR intentionally "
                    "empty (ADR 0013) — read blocks"
                ),
            )
        )
    elif source_block is not None:
        evidence.append(
            MatchEvidence(
                kind="multi_block_outcome_escalated",
                fields=(("source_block", source_block.index),),
                reason=f"outcome from block {source_block.index}: {outcome.name}",
            )
        )
    context_ref: ContextReference | None = metadata.reply_to
    correlation: CorrelationRequest | None = None
    if metadata.message_event is MessageEvent.EDIT:
        context_ref = context_ref or ContextReference(
            provider_name=metadata.provider_name,
            kind=ContextReferenceKind.EDITED_ORIGINAL,
        )
        correlation = CorrelationRequest(
            kind=CorrelationRequestKind.EDIT_APPLY, target=context_ref
        )
    return CanonicalParserIR(
        candidates=(),
        unresolved_fields=(),
        fragments=(),
        conflicts=(),
        ambiguities=(),
        evidence=tuple(evidence),
        normalization_decisions=normalized.normalization_decisions,
        conditions=(),
        provider_id=metadata.provider_name,
        parser_version=PARSER_VERSION,
        context_reference=context_ref,
        correlation_request=correlation,
        source_ref=metadata.source_reference,
    )


def _aggregate_block_results(
    metadata: MessageMetadata,
    normalized: NormalizedMessage,
    unit_results: list[tuple[MessageBlock, ParseResultState, CanonicalParserIR]],
) -> ParseResult:
    """Deterministic message-level aggregation of per-block results
    (ADR 0013 §5).

    Escalation order (mirrors §14 per-unit precedence, applied at message
    level): MALFORMED > UNSUPPORTED > AMBIGUOUS. Among non-escalating
    results: exactly one PARSED block → its outcome and IR are promoted
    (backward-compatible single-signal semantics); more than one →
    MULTI_SIGNAL with an explicitly empty top-level IR; none → PARTIAL
    when any block is PARTIAL, else NO_SIGNAL. Duplicate feed sections
    are marked ``duplicate_of`` (comparison-only) and never collapsed.
    """
    block_parses: list[BlockParse] = []
    first_seen: dict[tuple[tuple[object, object], ...], int] = {}
    for block, outcome, ir in unit_results:
        fingerprint = _block_fingerprint(ir)
        duplicate_of: int | None = None
        if fingerprint is not None:
            duplicate_of = first_seen.get(fingerprint)
            if fingerprint not in first_seen:
                first_seen[fingerprint] = block.index
        block_parses.append(
            BlockParse(block=block, outcome=outcome, ir=ir, duplicate_of=duplicate_of)
        )

    outcomes = [outcome for _, outcome, _ in unit_results]
    parsed_indices = [i for i, o in enumerate(outcomes) if o is ParseResultState.PARSED]
    escalated: ParseResultState | None = None
    if ParseResultState.MALFORMED in outcomes:
        escalated = ParseResultState.MALFORMED
    elif ParseResultState.UNSUPPORTED in outcomes:
        escalated = ParseResultState.UNSUPPORTED
    elif ParseResultState.AMBIGUOUS in outcomes:
        escalated = ParseResultState.AMBIGUOUS

    if escalated is not None:
        source_index = outcomes.index(escalated)
        return ParseResult(
            outcome=escalated,
            ir=_aggregate_ir(
                metadata,
                normalized,
                unit_results,
                escalated,
                unit_results[source_index][0],
            ),
            blocks=tuple(block_parses),
        )
    if len(parsed_indices) >= 2:
        return ParseResult(
            outcome=ParseResultState.MULTI_SIGNAL,
            ir=_aggregate_ir(
                metadata,
                normalized,
                unit_results,
                ParseResultState.MULTI_SIGNAL,
                None,
            ),
            blocks=tuple(block_parses),
        )
    if len(parsed_indices) == 1:
        return ParseResult(
            outcome=ParseResultState.PARSED,
            ir=unit_results[parsed_indices[0]][2],
            blocks=tuple(block_parses),
        )
    if ParseResultState.PARTIAL in outcomes:
        return ParseResult(
            outcome=ParseResultState.PARTIAL,
            ir=_aggregate_ir(
                metadata,
                normalized,
                unit_results,
                ParseResultState.PARTIAL,
                None,
            ),
            blocks=tuple(block_parses),
        )
    return ParseResult(
        outcome=ParseResultState.NO_SIGNAL,
        ir=_aggregate_ir(
            metadata,
            normalized,
            unit_results,
            ParseResultState.NO_SIGNAL,
            None,
        ),
        blocks=tuple(block_parses),
    )


def _parse_sectioned(
    raw: RawMessage,
    metadata: MessageMetadata,
    runtime: ProfileRuntime,
    normalized: NormalizedMessage,
    positioned: tuple[tuple[int, int, Token], ...],
    tokenize_violations: tuple[_Violation, ...],
    blocks: tuple[MessageBlock, ...],
) -> ParseResult:
    """Parse a sectioned message per block (ADR 0013).

    One message-level tokenization (spans stay global; the SourceMap is
    never re-based), then per-block candidate extraction + rule
    evaluation + resolution through the SAME unit core as whole-message
    parses. Message-level structural bounds (§15.3) reject the message
    before block evaluation."""
    if tokenize_violations:
        return build_parse_result(
            raw,
            metadata,
            runtime,
            None,
            normalized,
            None,
            (),
            tokenize_violations,
            (),
            _collect_rule_flags(runtime),
        )
    rule_flags = _collect_rule_flags(runtime)
    line_windows = _line_windows(raw.raw_text, normalized)
    # Tokens are emitted in normalized order, so each block's token slice
    # is found by binary search instead of a full-message scan per block
    # (Phase 2F adversarial audit: keeps sectioned parsing linear in the
    # message token count).
    token_starts = [s for s, _, _ in positioned]
    block_line_windows = _clip_line_windows_all(line_windows, blocks)
    unit_results: list[tuple[MessageBlock, ParseResultState, CanonicalParserIR]] = []
    for block in blocks:
        lo = bisect_left(token_starts, block.norm_start)
        hi = bisect_left(token_starts, block.norm_end)
        block_tokens = tuple(t for t in positioned[lo:hi] if t[1] <= block.norm_end)
        graph, _, extract_violations = extract_candidates(block_tokens, runtime)
        matches, rule_violations, unsupported, site_candidates = evaluate_rules(
            block_tokens,
            normalized,
            metadata,
            runtime,
            raw.raw_text,
            unit_bounds=(block.norm_start, block.norm_end),
            line_windows=block_line_windows[block.index],
        )
        merged_graph = _merge_candidate_graphs(graph, site_candidates)
        unit = _unit_core(
            raw,
            metadata,
            runtime,
            normalized,
            merged_graph,
            matches,
            extract_violations + rule_violations,
            unsupported,
            rule_flags,
        )
        unit_results.append((block, unit.outcome, unit.ir))
    return _aggregate_block_results(metadata, normalized, unit_results)
