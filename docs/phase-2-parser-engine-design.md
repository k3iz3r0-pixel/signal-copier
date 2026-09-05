# Phase 2 — Parser Engine Design Document

Status: DESIGN ONLY. No Python parser, regex engine, provider adapter,
Telegram/Discord ingestion, broker adapter, execution/strategy/risk/database/
replay/analytics/AI code is to be written from this document alone.

Phase reference: `docs/phase-status.md`, `docs/architecture.md`,
`AGENTS.md`, `docs/phase-1-signal-core-design.md` (frozen),
`docs/canonical-snapshot-contract.md` (frozen), `docs/principles.md`,
`docs/agent_instructions.md`.

This design assumes the Phase 1 contract is frozen and authoritative:
`Signal`, `SignalIdentity`, `SignalRevision`, `SignalEvent`,
`SignalInstruction`, the unified `ALLOWED_SNAPSHOT_TYPES`, the
`canonical_fingerprint` contract, and the canonical-snapshot projection
contract.

---

## Classification Legend (Anti-Hallucination)

Every design element in this document is tagged with exactly one of:

| Tag | Meaning |
|-----|---------|
| `REQUIREMENT` | Mandated by the approved Phase 2 brief or by AGENTS.md / Phase 1 contract. |
| `DESIGN DECISION` | Chosen among alternatives by this design; rationale is given. |
| `INFERENCE` | Derived from visible provider capability evidence; not directly observed as a full rule set. |
| `ASSUMPTION` | Adopted as a working basis without full verification; stated explicitly. |
| `OPEN QUESTION` | Deliberately deferred; not resolved in this design. |

When provider-specific behavior cannot be established from evidence, the
document states:

```text
UNKNOWN — REQUIRES PROVIDER EVIDENCE
```

The reference provider configuration screenshot is evidence ONLY for the
capability categories it visibly demonstrates. This design treats it as a
capability list, never as a complete provider rule set. No provider is
described as if its exact syntax were observed unless this document says so.

---

## 1. Goals

1. `REQUIREMENT` — Design a deterministic, provider-agnostic parsing
   platform supporting 20+ signal providers with substantially different
   message languages, layouts, conventions, and action semantics.
2. `REQUIREMENT` — Design the parser as a deterministic compiler-like
   pipeline, NOT as a collection of giant regular expressions. Regex is a
   low-level lexical matching mechanism inside a larger deterministic
   signal-language architecture.
3. `REQUIREMENT` — Support signal creation, modification, actions,
   pending-order actions, partial/full close, conditional actions,
   breakeven, trailing, SL/TP/entry modification, edits, deletes, replies,
   follow-up messages, multi-message signals, and multiple signals in one
   message.
4. `REQUIREMENT` — Keep provider-specific syntax, vocabulary, extraction
   rules, and context requirements outside the generic parser engine.
5. `REQUIREMENT` — Preserve explicit ambiguity; never silently reinterpret
   malformed or ambiguous input.
6. `REQUIREMENT` — Produce a parser-level Canonical IR between provider
   syntax and Signal Core; Signal Core receives only resolved canonical
   semantics.
7. `REQUIREMENT` — Treat provider message content as untrusted input; bound
   work, reject pathological input, preserve raw input and evidence.
8. `REQUIREMENT` — Make the parser testable without Telegram, Discord, or
   any broker.
9. `DESIGN DECISION` — Distinguish six discrete parse outcomes: PARSED,
   PARTIAL, AMBIGUOUS, MALFORMED, UNSUPPORTED, NO_SIGNAL.

---

## 2. Non-Goals (deferred; explicit)

1. Telegram / Discord / API / manual ingestion adapters (Phase 3+
   territory; only `RawMessage` and `MessageMetadata` are defined here).
2. Broker adapters, order submission, `ExecutionIntent` concrete
   implementation, `Order`, `Position` (deferred).
3. Strategy engine, risk engine, lot sizing, quantity allocation
   (deferred).
4. Database persistence, Redis, analytics, replay engine, backtesting
   (deferred).
5. AI / ML inference in any path (forbidden by `AGENTS.md` §26 and the
   Phase 1 contract).
6. Serialization framework dependency.
7. New Python dependencies. The parser uses the Python standard library
   and Phase 1 (zero new deps).
8. Evaluation of broker/account state by the parser (e.g., "is the trade
   in profit?"). Conditions are REPRESENTED, never evaluated, by the
   parser.
9. Confidence scores. The parser emits discrete states plus evidence; it
   does not emit probability.

---

## 3. Definition: "Signal Copier" Parser

The "Signal Copier" parser is the subsystem that converts one or more raw
provider messages into either:

A. a `Signal` (or `SignalInstruction` that produces a `Signal` revision
   when content changes),
B. a `SignalInstruction` (an action against an existing signal),
C. an explicit NON-SIGNAL result (NO_SIGNAL / MALFORMED / UNSUPPORTED /
   AMBIGUOUS / PARTIAL with explicit reasons and evidence).

The parser is **provider-agnostic** (it does not know about Telegram
channels, Discord servers, broker symbols, or specific provider names)
and **broker-agnostic** (it produces canonical `InstructionType` values,
not broker order types).

The parser is **deterministic** for any given `(RawMessage,
MessageMetadata, ProviderProfile)` triple. Same input → same output, same
evidence, same result state. `DESIGN DECISION`

---

## 4. Architecture

### 4.1 Compiler-Like Pipeline

`REQUIREMENT` — the parser is a deterministic compiler-like pipeline with
these separated stages:

```text
Raw Message
  → Message Normalization
  → Lexical Analysis
  → Candidate Extraction
  → Rule/Grammar Evaluation
  → Semantic Resolution
  → Conflict/Ambiguity Analysis
  → Canonical Parser IR
  → Context/Correlation (Phase 3+ boundary)
  → Signal Core integration (OUTPUT ADAPTER)
```

Layered decomposition:

```text
+--------------------------------------------------------------+
| 1. RawMessage + MessageMetadata (Phase 2 types; no provider  |
|    import)                                                   |
|    - raw_text (verbatim), media_refs, raw_payload_hash       |
|    - provider_name, source_type, source_reference,           |
|      timestamp_utc, message_event, reply_to, edit/delete     |
+--------------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------------+
| 2. ProviderProfile (declarative, loaded from registry)       |
|    - ProviderCapabilities, RuleSet, aliases, separators      |
+--------------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------------+
| 3. PARSER PIPELINE (pure deterministic functions)            |
|    raw -> normalize -> tokenize -> extract candidates ->     |
|    evaluate rules -> resolve semantics -> conflict/ambiguity |
|    -> canonical parser IR                                     |
+--------------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------------+
| 4. CONTEXT / CORRELATION BOUNDARY (Phase 3+; contract only)  |
|    - CorrelationRequest produced by parser; consumed by      |
|      correlation layer                                       |
+--------------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------------+
| 5. OUTPUT ADAPTER (Phase 2 boundary definition)              |
|    - CanonicalParserIR -> Signal OR SignalInstruction OR     |
|      explicit non-signal result                              |
+--------------------------------------------------------------+
```

### 4.2 Provider Independence Principle

`REQUIREMENT` — The parser pipeline must be implementable and testable
without importing any provider (Telegram, Discord, broker, API). The only
provider-aware input is the `ProviderProfile` declarative object.

No module in `packages/parser/` may import `telegram`, `discord`,
`telethon`, `pyrogram`, `mt4`, `mt5`, `ctrader`, `dxtrade`, or
`tradelocker`. (Enforced by an architectural-boundary test reserved for
Phase 3+ implementation; not written in Phase 2 design.)

### 4.3 Lifecycle / State Coupling Ban

`REQUIREMENT` — The parser MUST NOT introduce or reintroduce:

- `MODIFIED` as a `LifecycleState` (only `DRAFT`, `ACTIVE`, `CANCELLED`,
  `EXPIRED`, `ARCHIVED` are valid; `MODIFIED` was removed in Phase 1).
- `EXECUTING` / `EXECUTED` as `LifecycleState` values (they remain only
  `EventType` values; lifecycle is for the signal itself).
- Any shim that secretly promotes `UNSPECIFIED` to `MARKET` (Phase 1
  information-preservation principle).

The parser produces `EventType` and `InstructionType` values that already
exist in `packages.signal_core.enums`. No new `EventType` or
`InstructionType` member may be introduced by the parser.

### 4.4 Determinism and Time

`REQUIREMENT` —

- The parser does not call `time.time()`, `datetime.now()`,
  `uuid.uuid4()`, or read environment variables during parsing.
- All timestamps come from `MessageMetadata`.
- All UUIDs needed downstream are produced by the integration layer, not
  the parser.
- Randomness is forbidden in the parser pipeline.

### 4.5 Pure-Stage Design

`DESIGN DECISION` — Every pipeline stage is a pure function. No stage
reads or writes global state. State passes through the value chain via
immutable tuples and frozen dataclasses (validated by Phase 1's
`ALLOWED_SNAPSHOT_TYPES` contract where applicable).

### 4.6 Stage Responsibilities

| Stage | Input | Output | Responsibility |
|-------|-------|--------|----------------|
| Normalize | `RawMessage` | `NormalizedMessage` | Strip noise; collapse whitespace; canonicalize separators; produce `SourceMap` (§5.5.1); preserve raw + normalization decisions. |
| Tokenize (Lexical) | `NormalizedMessage` | `tuple[Token, ...]` | Lexical units (NUMBER, KEYWORD, SYMBOL, PUNCT, WHITESPACE, TEXT, EMOJI). |
| Extract Candidates | `tuple[Token, ...] + ProviderProfile` | `CandidateGraph` | Identify competing candidates (symbol, price, keyword, direction). |
| Evaluate Rules | `CandidateGraph + ProviderProfile` | `tuple[RuleMatch, ...]` | Apply `ProviderRule`s; bind candidates to rule slots. |
| Resolve Semantics | `tuple[RuleMatch, ...]` | `tuple[ParsedFragment, ...]` | Convert rule matches into canonical semantic fragments. |
| Conflict/Ambiguity | `tuple[ParsedFragment, ...]` | `tuple[Conflict, ...] + tuple[Ambiguity, ...]` | Detect missing, conflicting, ambiguous fields. |
| Build Canonical IR | fragments + conflicts + ambiguities + evidence | `CanonicalParserIR` | Provider-syntax-free intermediate representation. |

The OUTPUT ADAPTER then converts the `CanonicalParserIR` into either a
`Signal`, a `SignalInstruction`, or an explicit non-signal result.

---

## 5. Mandatory Concept Contracts

The approved brief mandates contracts for these 21 concepts. This section
defines each. `REQUIREMENT` for all 21; sub-decisions tagged inline.

### 5.1 RawMessage

`REQUIREMENT` — the untouched provider payload, before interpretation.

```text
@dataclass(frozen=True, slots=True)
class RawMessage:
    raw_text:            str        # original text, NEVER mutated
    media_refs:          tuple[MediaKind, ...]  # IMAGE | VIDEO | DOCUMENT | NONE
    raw_payload_hash:    str        # SHA-256 of raw_text (for dedup)
```

`DESIGN DECISION` — `raw_payload_hash` (SHA-256 of `raw_text`) is a
message-identity/dedup hash of the raw payload. It is DISTINCT from the
canonical semantic fingerprint (SHA-256 of the canonical snapshot per
`docs/canonical-snapshot-contract.md`). The parser never uses
`raw_payload_hash` as a semantic fingerprint, and never uses the
canonical fingerprint for raw-message dedup (see also §13.3).

### 5.2 MessageMetadata

`REQUIREMENT` — provider/source identity and message lifecycle, separated
from the raw payload.

```text
@dataclass(frozen=True, slots=True)
class MessageMetadata:
    provider_name:       str        # e.g., "provider_alpha" (not Telegram)
    source_type:         SourceType # TELEGRAM / DISCORD / MANUAL / API
    source_reference:    str | None # provider-side message ID
    timestamp_utc:       datetime   # message timestamp (UTC, tz-aware)
    message_event:       MessageEvent  # CREATE | EDIT | DELETE | FOLLOW_UP
    reply_to:            ContextReference | None
    provenance_extra:    tuple[tuple[str, object], ...]  # constrained
                                                          # to ALLOWED_SNAPSHOT_TYPES
```

`DESIGN DECISION` — `RawMessage` (payload) and `MessageMetadata`
(identity/lifecycle) are separate so the raw payload can be preserved and
hashed without being entangled with source-specific fields.

### 5.3 NormalizedMessage

`REQUIREMENT` — the derived working view of the raw message.

```text
@dataclass(frozen=True, slots=True)
class NormalizedMessage:
    normalized_text:     str        # derived; raw_text is preserved
    source_map:          SourceMap  # normalized<->raw offset mapping (§5.5.1)
    normalization_decisions: tuple[str, ...]  # e.g., "strip_markdown",
                                              # "collapse_whitespace",
                                              # "nfkc_symbols"
```

### 5.4 Token

`REQUIREMENT` — a single lexical unit produced by Lexical Analysis.

```text
@dataclass(frozen=True, slots=True)
class Token:
    category:            TokenCategory  # NUMBER | KEYWORD | SYMBOL |
                                        # PUNCT | WHITESPACE | TEXT | EMOJI
    text:                str
    source_span:         SourceSpan
```

### 5.5 SourceSpan

`REQUIREMENT` — character offsets into the RAW text, preserved end-to-end
for evidence.

```text
@dataclass(frozen=True, slots=True)
class SourceSpan:
    start:               int   # inclusive char offset into raw_text
    end:                 int   # exclusive char offset into raw_text
    source_reference:    str | None  # provider-side message ID
```

`REQUIREMENT` — `SourceSpan` offsets are ALWAYS raw-text offsets. When a
span is computed from normalized text (tokens, candidates, rule matches,
conflicts, ambiguities), it is converted to a raw span via the `SourceMap`
projection (§5.5.1) BEFORE it is stored. Normalized offsets never appear
in any `SourceSpan`.

### 5.5.1 SourceMap — Normalized ↔ Raw Offset Mapping (Authoritative)

`REQUIREMENT` — normalization changes the text, so a `Token` produced from
`NormalizedMessage.normalized_text` must never be assumed to share offsets
with `raw_text`. This section defines the ONLY lawful way to derive raw
offsets, and guarantees that every candidate / rule / evidence span traces
back to the exact original raw characters.

`SourceMap` (frozen value object):

```text
@dataclass(frozen=True, slots=True)
class SourceMap:
    char_ranges:     tuple[tuple[int, int], ...]      # len == len(normalized_text)
                                                     # entry i = (raw_start, raw_end)
                                                     # of the raw chars that
                                                     # produced normalized char i
    deleted_ranges:  tuple[tuple[int, int, str], ...] # (raw_start, raw_end, op_name)
                                                     # raw ranges removed by a
                                                     # named normalization op
```

Invariants (enforced by construction; verified by Phase 3+ tests):

- `len(char_ranges) == len(normalized_text)`. Every normalized character
  has a non-empty raw source range (≥ 1 raw char). One raw char may source
  several normalized chars (NFKC expansion); one normalized char may source
  several raw chars (collapsing). Both are legal.
- `deleted_ranges` and the source ranges in `char_ranges` together account
  for every raw offset in `[0, len(raw_text))` exactly once, with a single
  provenance. No raw offset is unaccounted-for and none is double-counted
  with conflicting provenance.
- Monotonicity: the raw start offsets in `char_ranges` are non-decreasing
  in normalized index; `deleted_ranges` are ordered and non-overlapping.
  Normalization NEVER reorders characters (bidi is a rendering concern;
  the parser operates on logical order and removes/rejects bidi controls,
  see §16.2).

Projection contract:

```text
raw_span_for(norm_start, norm_end) =
    (char_ranges[norm_start][0], char_ranges[norm_end - 1][1])
```

for any non-empty normalized range `[norm_start, norm_end)`. The result is
the minimal contiguous raw interval covering every raw source character of
the normalized range; any characters deleted by normalization that lie
inside that interval are part of the original message and therefore part
of the evidence span. Every `Token.source_span`, `Candidate.source_span`,
`RuleMatch.span`, `Conflict.spans`, `Ambiguity.spans`, and
`MatchEvidence.span` MUST be a raw span computed by this projection —
never a normalized offset.

Canonical normalization pipeline (FIXED order; each step is a pure
function `(text, SourceMap) -> (text', SourceMap')` and appends its op
name to `normalization_decisions`):

1. `strip_control_only` — remove zero-width characters
   (U+200B..U+200D, U+FEFF) and bidi/format controls
   (U+202A..U+202E, U+2066..U+2069). Removed chars are recorded as
   `deleted_ranges` with op `"strip_zero_width"` / `"strip_bidi_control"`.
   If nothing remains, the message is MALFORMED with evidence
   `zero_width_only` / `bidi_control_only` (§16.2).
2. `unicode_normalize` — apply NFKC to the remaining text. Character count
   may change; `char_ranges` is rebuilt at character granularity so every
   normalized char still resolves to its raw source range(s).
3. `strip_markdown_html` (per Profile) — remove Markdown/HTML syntax
   characters (emphasis markers, link syntax, code fences) while
   preserving their content; removed syntax chars are recorded as
   `deleted_ranges` with op `"strip_markdown"`.
4. `collapse_whitespace` — every whitespace run maps to one canonical
   space U+0020 whose raw range is the entire original run.
5. `canonicalize_separators` (per Profile) — normalize field/multi-value
   separators (em-dash, full-width punctuation, non-ASCII dashes) to the
   profile's canonical separator; character-granular mapping applied; op
   `"separator_canonicalization"`.

The pipeline order is FIXED and documented here; no stage may be
reordered, skipped, or added without an ADR (offset correctness is
sensitive to order).

`DESIGN DECISION` — `SourceMap` lives in `NormalizedMessage`
(pipeline-internal). Downstream types carry only raw `SourceSpan`s; they
do not carry normalized offsets. The `CanonicalParserIR` therefore does
not need to store the map for spans to remain traceable to raw text.

### 5.6 Candidate

`REQUIREMENT` — a single competing hypothesis for one semantic slot. A
candidate is NOT collapsed into a dict value; it preserves provenance.

```text
@dataclass(frozen=True, slots=True)
class Candidate:
    slot:                CandidateSlot  # DIRECTION | INSTRUMENT | ENTRY |
                                        # ENTRY_GEOMETRY | ENTRY_TRIGGER |
                                        # SL | TP | ACTION | CONDITION |
                                        # METADATA | PRICE | RANGE
    value:               object   # canonical-typed value (TradeDirection,
                                  # Price, PriceRange, str, ...)
    source_span:         SourceSpan
    provenance:          tuple[MatchEvidence, ...]  # evidence chain
```

### 5.7 CandidateGraph

`REQUIREMENT` — preserves multiple competing candidates per slot before
resolution.

```text
@dataclass(frozen=True, slots=True)
class CandidateGraph:
    by_slot:             tuple[tuple[CandidateSlot, tuple[Candidate, ...]], ...]
    # Deterministic ordering: slots sorted by enum order; candidates
    # sorted by (source_span.start, source_span.end, provenance length).
```

See §6 (Candidate Model) for resolution classification.

### 5.8 MatchEvidence

`REQUIREMENT` — provenance record explaining WHY a candidate, rule match,
or conflict exists.

```text
@dataclass(frozen=True, slots=True)
class MatchEvidence:
    kind:               str    # "rule_match" | "conflict" | "lex_fallback" |
                               # "normalization" | "provider_override" | ...
    rule_id:            str | None
    span:               SourceSpan | None
    snippet:            str | None          # the matched raw text
    fields:             tuple[tuple[str, object], ...]
    reason:             str | None          # human-readable explanation
```

### 5.9 RuleMatch

`REQUIREMENT` — a rule that fired, with bound candidates.

```text
@dataclass(frozen=True, slots=True)
class RuleMatch:
    rule_id:            str
    category:           str         # ENTRY | SL | TP | ACTION_* | ...
    span:               SourceSpan
    bindings:           tuple[tuple[str, Candidate], ...]  # slot -> candidate
    evidence:           tuple[MatchEvidence, ...]
```

### 5.10 Conflict

`REQUIREMENT` — two or more non-compatible interpretations for the SAME
slot (contradiction, not mere multiplicity).

```text
@dataclass(frozen=True, slots=True)
class Conflict:
    kind:               ConflictKind  # CONFLICTING
    slot:               CandidateSlot
    involved:           tuple[Candidate, ...]   # the competing candidates
    spans:              tuple[SourceSpan, ...]
    reason:             str
```

### 5.11 Ambiguity

`REQUIREMENT` — multiple valid interpretations that the parser cannot
resolve without context (not a contradiction; genuine underdetermination).

```text
@dataclass(frozen=True, slots=True)
class Ambiguity:
    kind:               AmbiguityKind  # AMBIGUOUS_TRIGGER | AMBIGUOUS_RANGE
                                       # | AMBIGUOUS_PERCENT | ...
    slot:               CandidateSlot | None
    candidates:         tuple[Candidate, ...]
    spans:              tuple[SourceSpan, ...]
    reason:             str
```

`DESIGN DECISION` — `Conflict` (contradiction) and `Ambiguity`
(underdetermination) are distinct types, so downstream layers can treat
"two SL values" differently from "could be LIMIT or STOP".

### 5.12 ParsedFragment

`REQUIREMENT` — a partial semantic result for one aspect of a message,
used for multi-message signals and follow-ups.

```text
@dataclass(frozen=True, slots=True)
class ParsedFragment:
    slot:               CandidateSlot
    value:              object    # canonical type (Price, TradeDirection, ...)
    state:              FragmentState  # RESOLVED | UNRESOLVED | CONDITIONAL
    condition:          tuple[Condition, ...]   # deterministic predicates
    evidence:           tuple[MatchEvidence, ...]
    context_requirement: ContextRequirement  # NONE | REPLY_REQUIRED |
                                             # CONTEXT_REQUIRED | LAST_SIGNAL
```

### 5.13 CanonicalParserIR

`REQUIREMENT` — the provider-syntax-free IR between parsing and Signal
Core. See §13 for the full preservation contract.

### 5.14 ParseResult

`REQUIREMENT` — the outcome wrapper returned by the parser.

```text
@dataclass(frozen=True, slots=True)
class ParseResult:
    outcome:            ParseResultState  # PARSED | PARTIAL | AMBIGUOUS |
                                          # MALFORMED | UNSUPPORTED | NO_SIGNAL
    ir:                 CanonicalParserIR
```

### 5.15 ProviderProfile

`REQUIREMENT` — declarative definition of one provider.

```text
@dataclass(frozen=True, slots=True)
class ProviderProfile:
    provider_name:           str
    capabilities:            ProviderCapabilities
    rule_set:                RuleSet
    symbol_aliases:          tuple[tuple[str, str], ...]
    tokenizer_pattern:       str      # single compiled alternation
    field_separators:        tuple[str, ...]
    multi_value_separators:  tuple[str, ...]
    decimal_format:          str      # regex
    range_patterns:          tuple[str, ...]
    multiline_mode:          bool
    reply_requirement:       ReplyRequirement
    edit_behavior:           EditBehavior
    delete_behavior:         DeleteBehavior
    follow_up_behavior:      FollowUpBehavior
    max_message_length:      int      # default 8000; bounded
    max_numeric_value:       Decimal  # default 1e12
    version:                 str
```

### 5.16 ProviderCapabilities

`REQUIREMENT` — what a provider CAN express, declared separately from how
it is parsed (see §12.4). Flags mirror the reference capability categories:

```text
@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    close_full:            bool   # close fully by keyword
    close_half:            bool   # close half by keyword
    profit_close:          bool   # profit-conditioned partial close
    move_sl_breakeven:     bool   # move SL to entry / breakeven
    remove_sl:             bool   # remove SL
    cancel_pending:        bool   # cancel pending order
    trigger_pending:       bool   # trigger pending order
    move_sl_number:        bool   # change SL using number after keyword
    move_sl_conditional:   bool   # change SL conditionally on keyword
    move_tp_conditional:   bool   # change TP conditionally
    move_entry_conditional: bool  # change entrypoint conditionally
    edit_handling:         bool   # original-message edit handling
    delete_handling:       bool   # original-message deletion handling
    reply_required:        bool   # provider reply requirements
    negative_keywords:     bool   # negative keyword exclusions
    last_signal_execution: bool   # execution against the last signal
    trailing:              bool   # trailing stop
    multi_signal:          bool   # multiple signals in one message
    multi_message:         bool   # one signal across messages
```

`INFERENCE` — the flag set above is inferred from the visible capability
categories in the reference screenshot. The exact per-provider flag values
are:

```text
UNKNOWN — REQUIRES PROVIDER EVIDENCE
```

### 5.17 ProviderRule

`REQUIREMENT` — a single declarative parsing rule. See §7 (Rule System).

### 5.18 RuleSet

`REQUIREMENT` — an ordered, inheritable collection of `ProviderRule`s.

```text
@dataclass(frozen=True, slots=True)
class RuleSet:
    rules:               tuple[ProviderRule, ...]   # own rules, priority-ordered
    parent:              str | None                 # single parent RuleSet name;
                                                    # multiple inheritance PROHIBITED
    overrides:           tuple[tuple[str, str], ...]  # (rule_id, inherited_rule_id)
                                                    # own rule masks inherited rule
    exclusions:          tuple[str, ...]            # inherited rule_ids excluded
```

### 5.19 Rule Inheritance / Override

`REQUIREMENT` — a `RuleSet` may declare a single `parent`; rules are
inherited and may be overridden by re-declaring the same `rule_id` in a
more-derived `RuleSet`. Full deterministic resolution — parent
linearization, override precedence, exclusions, duplicate rule IDs,
missing parents, inheritance cycles, conflicting overrides,
provider/domain/common precedence, and version compatibility — is defined
in §12.5. Multiple inheritance is PROHIBITED. See §12 (Provider
Architecture).

### 5.20 ContextReference

`REQUIREMENT` — a reference to a prior message/signal needed to interpret
the current message.

```text
@dataclass(frozen=True, slots=True)
class ContextReference:
    provider_name:       str
    source_reference:    str | None
    signal_identity:     SignalIdentity | None   # resolved by correlation layer
    kind:                ContextReferenceKind    # REPLY | QUOTE | LAST_SIGNAL
                                                   # | EDITED_ORIGINAL | NONE
```

### 5.21 CorrelationRequest

`REQUIREMENT` — what the parser asks the correlation layer to do. The
parser DOES NOT perform correlation; it emits the request.

```text
@dataclass(frozen=True, slots=True)
class CorrelationRequest:
    kind:                CorrelationRequestKind  # TARGET_LAST_SIGNAL |
                                                 # TARGET_REPLIED_SIGNAL |
                                                 # MULTI_MESSAGE_APPEND |
                                                 # EDIT_APPLY | DELETE_APPLY |
                                                 # NONE
    target:              ContextReference | None
    fragments:           tuple[ParsedFragment, ...]  # semantic fragments to
                                                     # be correlated
```

---

## 6. Candidate Model

### 6.1 No Immediate Collapse

`REQUIREMENT` — extracted information is NOT immediately collapsed into a
dict. The `CandidateGraph` preserves multiple competing candidates per
slot until resolution.

Example:

```text
direction:
  candidate A = BUY   (span 10-13, evidence [rule_match:provider_alpha.direction])
  candidate B = SELL  (span 28-32, evidence [rule_match:provider_alpha.direction])
```

### 6.2 Resolver Classification

`REQUIREMENT` — the resolver distinguishes exactly these relationships
between competing candidates:

| Relationship | Meaning | Action |
|--------------|---------|--------|
| `compatible` | Candidates occupy different slots, or the same slot with identical values from independent evidence. | Keep both; merge evidence. |
| `duplicate` | Same slot, same value, same span, different rule IDs. | Collapse to one candidate with merged evidence. |
| `conflicting` | Same slot, different values (contradiction). | Emit `Conflict`; outcome ≥ AMBIGUOUS or MALFORMED per §14. |
| `ambiguous` | Same slot, multiple valid values with no contradiction (e.g., trigger could be LIMIT or STOP). | Emit `Ambiguity`; outcome = AMBIGUOUS. |

`DESIGN DECISION` — **rule override is NOT a candidate relationship.** It
is resolved BEFORE candidate extraction, at rule-evaluation time (§12.5):
when a provider rule overrides an inherited rule, the inherited rule
simply does not fire for that provider, so only one rule (and one
candidate) is produced. The fact that an override occurred is recorded as
`MatchEvidence` with `kind = "provider_override"` and the pair
`(rule_id, base_rule_id)` in `fields` — this is override PROVENANCE, not a
resolver outcome. If a provider rule and an inherited rule both
nevertheless produce candidates for the same slot, those candidates are
classified as `duplicate` (same value) or `conflicting` (different values)
like any other candidates; the override evidence is carried alongside,
not instead of, that classification.

### 6.3 Provenance

`REQUIREMENT` — every candidate preserves provenance (`MatchEvidence`) so
the resolver can explain every choice. Resolution is deterministic:
candidates are compared in a fixed order (slot enum order, then span
order, then provenance length).

---

## 7. Rule System

### 7.1 Rule Primitives

`REQUIREMENT` — the rule system supports at minimum these primitives. Do
NOT encode all semantics in regex.

**Matcher:**

| Matcher | Meaning |
|---------|---------|
| `literal` | Exact keyword/text match (e.g., "CLOSE HALF"). |
| `regex` | Bounded regex (see §15). |
| `token_sequence` | Ordered token sequence (e.g., `SYMBOL NUMBER`). |
| `symbol` | Symbol-table lookup (canonical `Instrument`). |
| `alias` | Alias resolution (e.g., "GOLD" → "XAUUSD"). |
| `number` | A single number token. |
| `price` | A number interpreted as a price via `decimal_format`. |
| `price_range` | Two numbers joined by `range_patterns`. |

**Scope:**

| Scope | Meaning |
|-------|---------|
| `whole_message` | Match anywhere in the message. |
| `line` | Match within one line. |
| `section` | Match within a delimited section. |
| `after_token` | Match text after a given token. |
| `before_token` | Match text before a given token. |
| `between_anchors` | Match between two anchor tokens. |
| `reply` | Match in the replied-to message text. |
| `quoted_message` | Match in a quoted/forwarded segment. |

**Constraints:**

| Constraint | Meaning |
|------------|---------|
| `requires` | Rule fires only if another keyword/slot is present. |
| `forbids` | Rule does not fire if a forbidden keyword is present (negative keyword exclusions). |
| `required` | Anchor token/keyword matched but extraction target absent → provider grammar violation → MALFORMED (§14.2). |
| `requires_reply` | Rule fires only if `reply_to` is present. |
| `requires_context` | Rule fires only if a `ContextReference` is present. |
| `mutually_exclusive` | Only one of a group of rules may match. |
| `repeatable` | Rule may match multiple times (e.g., multiple TPs). |
| `uniqueness` | Rule matches at most once per message. |

`DESIGN DECISION` — occurrence selection is a `ProviderRule` FIELD
(`OccurrenceSelection`, §7.2), not a `Constraint`.

**Semantic targets:**

```text
direction | instrument | entry | entry_geometry | entry_trigger |
SL | TP | action | condition | metadata
```

### 7.2 ProviderRule Shape

`DESIGN DECISION` —

```text
@dataclass(frozen=True, slots=True)
class ProviderRule:
    id:               str   # stable string ("provider_alpha.entry.buy_limit")
    category:         str   # ENTRY | SL | TP | ACTION_* | ...
    matcher:          MatcherSpec
    scope:            ScopeSpec
    constraints:      tuple[Constraint, ...]
    target:           SemanticTarget
    priority:         int   # lower = higher priority
    occurrence:       OccurrenceSelection  # FIRST | LAST | NTH | ALL
```

### 7.3 Rule Evaluation

`DESIGN DECISION` — effective rules (§12.5) are evaluated grouped by
`category`; category groups are ordered lexicographically by `category`
name (a deterministic total order; category names are stable strings).
Within a category they are sorted by (`priority` ascending, then
`rule_id` lexicographic). Among rules matching overlapping text for
the same target, the LONGER raw match wins; equal length → lower
`priority`; equal priority → lexicographically smaller `rule_id`. This
total order is deterministic and documented (see §6.3).

### 7.4 Extraction Primitives

`REQUIREMENT` — first-class operations, visibly required by the reference
screenshot. Each is a named operation usable by `MatcherSpec` or
`ScopeSpec`:

```text
number_after_keyword      # e.g., "SL 3320" -> 3320
number_before_keyword     # e.g., "3320 SL" -> 3320
first_number              # first number token in scope
last_number               # last number token in scope
nth_number                # nth number token in scope (n = 1, 2, 3, ...)
text_after_keyword        # text following a keyword
text_before_keyword       # text preceding a keyword
between_two_anchors       # text between anchor A and anchor B
require_keyword           # pre-match constraint
forbid_keyword            # negative exclusion constraint
require_reply             # reply requirement constraint
target_last_signal        # correlation request: apply to last signal
target_replied_signal     # correlation request: apply to replied signal
```

`INFERENCE` — these map to the visible capability categories (change SL
using a number after a keyword, change SL conditionally if another keyword
exists, execution against the last signal, etc.). Exact provider
realizations are:

```text
UNKNOWN — REQUIRES PROVIDER EVIDENCE
```

---

## 8. Action Semantics

### 8.1 Actions Are Semantic Instructions

`REQUIREMENT` — actions are semantic instructions, NOT broker orders. The
parser emits `InstructionType` values already present in
`packages.signal_core.enums` (Phase 1 §3.11):

| Action | InstructionType | Notes |
|--------|-----------------|-------|
| OPEN | `OPEN` | Initiate a new signal. |
| MODIFY | `MODIFY` | General modification (entry change, conditional change). |
| CANCEL | `CANCEL` | Cancel an existing signal. |
| CLOSE | `CLOSE` | Close fully by keyword. |
| PARTIAL_CLOSE | `PARTIAL_CLOSE` | Close half / percent partial close. |
| MOVE_SL | `MOVE_SL` | Change SL (number after keyword, conditional). |
| MOVE_TP | `MOVE_TP` | Change TP (conditional). |
| BREAKEVEN | `BREAKEVEN` | Move SL to entry. |
| TRAIL | `TRAIL` | Trailing stop. |
| SCALE_IN | `SCALE_IN` | Expand entry levels. |
| SCALE_OUT | `SCALE_OUT` | Reduce exposure (execution-level). |
| REVERSE | `REVERSE` | Reverse direction. |

`REQUIREMENT` — the parser MUST NOT introduce new `InstructionType`
members. `TRIGGER_PENDING` remains an open question (§24) and is
represented in the IR as a `MODIFY` with a `trigger_pending` flag.

### 8.2 Conditions

`REQUIREMENT` — conditions such as "only if the trade is in profit" are
represented as deterministic predicates, never evaluated by the parser.

```text
@dataclass(frozen=True, slots=True)
class Condition:
    kind:            ConditionKind  # IN_PROFIT | AT_PRICE | KEYWORD_PRESENT |
                                    # NONE
    params:          tuple[tuple[str, object], ...]
```

The parser records the condition; a later strategy/execution layer decides
whether it is satisfied. `REQUIREMENT` — the parser MUST NOT evaluate
broker/account state.

---

## 9. Message Events

### 9.1 MessageEvent

`REQUIREMENT` — explicit message-event semantics, separate from Signal
lifecycle:

```text
MessageEvent = CREATE | EDIT | DELETE | FOLLOW_UP
```

| Event | Meaning |
|-------|---------|
| `CREATE` | A new, original message. |
| `EDIT` | An existing message was edited; latest text is in `raw_text`. |
| `DELETE` | An existing message was deleted. |
| `FOLLOW_UP` | A follow-up message that references or depends on a prior message. |

`REQUIREMENT` — message lifecycle (CREATE/EDIT/DELETE/FOLLOW_UP) is
separate from Signal lifecycle (DRAFT/ACTIVE/CANCELLED/EXPIRED/ARCHIVED).
A message event never directly sets a `LifecycleState`.

### 9.2 Edit Delta Representation

`REQUIREMENT` — an edited message is reparsed from its latest text and
represented as a DELTA, not as a brand-new signal:

```text
@dataclass(frozen=True, slots=True)
class EditDelta:
    added:       tuple[ParsedFragment, ...]
    changed:     tuple[tuple[ParsedFragment, ParsedFragment], ...]  # (before, after)
    removed:     tuple[ParsedFragment, ...]
    unchanged:   tuple[ParsedFragment, ...]
```

`REQUIREMENT` — revision application is NOT implemented in Phase 2. The
correlation layer (Phase 3+) compares fingerprints and decides whether a
`SignalRevision` is produced.

---

## 10. Context / Correlation Separation

### 10.1 Five Explicit Layers

`REQUIREMENT` — explicitly separate:

```text
A. lexical parsing        # RawMessage -> tokens/candidates
B. semantic parsing       # candidates -> ParsedFragments
C. signal correlation     # which signal do fragments target?   (Phase 3+)
D. revision generation    # edit deltas -> SignalRevision       (Phase 3+)
E. instruction generation # fragments -> SignalInstruction      (OUTPUT ADAPTER)
```

### 10.2 Worked Example

`REQUIREMENT` —

```text
Message A: BUY XAUUSD 3330
Message B: SL 3320
Message C: CLOSE HALF
```

- **A** (lexical + semantic): produces `ParsedFragment`s for direction,
  instrument, entry. Layer E produces a `Signal` (or IR → Signal via
  OUTPUT ADAPTER).
- **B** (lexical + semantic): produces a `ParsedFragment` for SL only,
  with `context_requirement = LAST_SIGNAL` and a `CorrelationRequest`
  `TARGET_LAST_SIGNAL`. Layer C decides which signal B targets.
- **C** (lexical + semantic): produces a `ParsedFragment` for
  `PARTIAL_CLOSE` (percent 50), with `CorrelationRequest`
  `TARGET_LAST_SIGNAL`. Layer C decides the target.

The parser produces semantic fragments and correlation requests; the
correlation layer (Phase 3+) resolves them. `REQUIREMENT` — correlation
state is NOT implemented in Phase 2.

---

## 11. Multi-Signal / Multi-Message

`REQUIREMENT` — the architecture must support, without assuming one
message equals one signal:

- one message containing multiple signals (multiple `ParsedFragment`
  groups keyed by a `signal_group_id`);
- one signal spread across multiple messages (fragments carry
  `context_requirement` + `CorrelationRequest MULTI_MESSAGE_APPEND`);
- follow-up actions (`FOLLOW_UP` + `TARGET_LAST_SIGNAL`);
- quoted/replied messages (`ContextReferenceKind.REPLY` / `QUOTE`);
- edits (`EDIT` → `EditDelta`);
- deletes (`DELETE` → `CorrelationRequest DELETE_APPLY`).

---

## 12. Provider Architecture

### 12.1 Rule Composition Chain

`REQUIREMENT` — the composition chain is a SINGLE-parent chain, resolved
deterministically (§12.5):

```text
Common rules (root)
  → domain-specific shared rules (forex / crypto / index)
    → provider profile (leaf)
      → provider overrides (re-declaration / renamed masking)
        → provider exclusions
```

Precedence is provider (leaf) > domain > common (root).

### 12.2 Adding Provider #21

`REQUIREMENT` — adding provider #21 must NOT require modifying generic
parser logic unless the provider exposes a genuinely new capability. The
steady-state path is: add a `ProviderProfile` + `RuleSet` + fixtures; no
parser code change.

### 12.3 New Capability Path

`DESIGN DECISION` — if a genuinely new capability appears, it is added as
a new `ProviderCapabilities` flag + new `ProviderRule` category, with an
ADR, and the generic engine is extended ONCE (not per-provider). This is
the only sanctioned reason to modify generic parser logic.

### 12.4 Capabilities vs Rules

`REQUIREMENT` — `ProviderCapabilities` (what a provider can express) is
declared separately from `ProviderRule`s (how it is parsed). Capabilities
are validated at profile load time; rules are interpreted at parse time.

`REQUIREMENT` — `ProviderCapabilities` remains CAPABILITY-ORIENTED: it
declares only WHAT a provider can express (booleans). It MUST NOT grow
into a mirror of provider syntax. Syntax and lexical specifics — keyword
vocabulary, separators, decimal/range formats, matcher patterns — belong
in the `ProviderProfile` syntax fields and in `ProviderRule`s, never as
capability flags. A capability flag exists only when (a) it is
meaningfully "can express X", and (b) downstream logic or validation
needs to branch on it independent of syntax. If a flag would duplicate
rule/grammar data, it is a rule, not a capability.

### 12.5 Effective RuleSet Resolution (Deterministic)

`REQUIREMENT` — for every `ProviderProfile` there is EXACTLY ONE
deterministic effective `RuleSet` (a `tuple[ProviderRule, ...]` computed
at profile load time). Resolution proceeds as follows; any violation is a
deterministic profile load error. A broken profile is rejected IN ITS
ENTIRETY — it can never produce a partial or silent parse.

1. **Single-parent linearization (multiple inheritance PROHIBITED).**
   `RuleSet.parent` is a single `RuleSet` name or `None`. The chain is
   linearized leaf→root: `[own, parent, parent.parent, …, root]`, where
   the root has `parent = None`. There is no list-valued parent; a
   profile needing multiple parents must be refactored into a chain or
   introduce a named intermediate RuleSet. (Introducing multiple
   inheritance requires a new ADR.)
2. **Missing parent.** Any `parent` name that does not resolve to a known
   RuleSet → load error `rule_set_parent_missing`.
3. **Inheritance cycle.** If the parent walk revisits any name → load
   error `rule_set_cycle`.
4. **Duplicate rule IDs within one RuleSet.** Two rules in the same
   `rules` tuple with the same `id` → load error `duplicate_rule_id`.
   (Re-using an id ACROSS levels is override-by-redeclaration; see 5.)
5. **Inheritance with re-declaration.** Fold the chain root→leaf: for
   each `ProviderRule` in order, insert into a map keyed by `id`. A rule
   whose `id` already exists REPLACES the earlier definition (its own
   matcher, constraints, target, priority, and occurrence win).
   Precedence: provider (leaf) > domain > common (root). This is the
   sole mechanism by which a derived level overrides a base rule with
   the SAME id.
6. **Exclusions.** Each `exclusions` entry names an inherited rule id
   that is removed from the effective set. It cannot name a rule declared
   in the SAME RuleSet's own `rules` (load error
   `exclusion_conflicts_with_declaration`). Exclusions are cumulative
   along the chain; an id excluded at any level is absent from the
   effective set. Excluding an unknown inherited id → load error
   `exclusion_unknown_rule`.
7. **Overrides (renamed masking).** `overrides` entries are
   `(rule_id, inherited_rule_id)`, meaning "this RuleSet's own rule
   `rule_id` masks (suppresses) the inherited rule `inherited_rule_id`".
   Validation: `rule_id` must be declared in THIS RuleSet's `rules`;
   `inherited_rule_id` must exist in the inherited effective set; a given
   `rule_id` appears in at most one entry; a given `inherited_rule_id` is
   targeted by at most one entry; an override may not target a rule that
   is also excluded. Violations → load error `conflicting_override`.
   Effect: the inherited target is removed from the effective set, and
   the replacement's provenance is recorded (§6.2).
8. **Version compatibility.** The engine declares the profile schema
   version(s) it supports. A `ProviderProfile.version` the engine does
   not support → load error `unsupported_profile_version`. Version is a
   `ProviderProfile`-level field (§5.15); `RuleSet` itself (§5.18)
   carries no version field. Rule ids are stable within a profile
   version; merging RuleSets whose owning profiles declare incompatible
   `ProviderProfile.version` values is not defined and is a load error
   `rule_set_version_mismatch` if attempted.

After resolution, the effective set is a `tuple[ProviderRule, ...]`
sorted once for evaluation (§7.3) and frozen. The resolution record —
which rules were inherited, re-declared, masked, excluded, and the
recorded override provenance — is available to the resolver for evidence
and to profile validators for auditing.

---

## 13. Canonical Parser IR

### 13.1 Preservation Contract

`REQUIREMENT` — the IR must preserve ALL of:

- extracted semantic candidates (`tuple[Candidate, ...]` after resolution);
- unresolved fields (slots present but unresolved — e.g., a percent SL
  waiting on entry price);
- evidence (`tuple[MatchEvidence, ...]`);
- source spans (`SourceSpan` on every candidate, match, conflict);
- rule IDs (`rule_id` on every `RuleMatch` and `MatchEvidence`);
- provider ID (`provider_name` from `MessageMetadata`);
- ambiguity reasons (`tuple[Ambiguity, ...]`);
- conflicts (`tuple[Conflict, ...]`);
- normalization decisions (from `NormalizedMessage`);
- message references (`ContextReference`);
- conditions (`tuple[Condition, ...]`).

### 13.2 IR Shape

```text
@dataclass(frozen=True, slots=True)
class CanonicalParserIR:
    candidates:           tuple[Candidate, ...]       # post-resolution
    unresolved_fields:    tuple[CandidateSlot, ...]
    fragments:            tuple[ParsedFragment, ...]
    conflicts:            tuple[Conflict, ...]
    ambiguities:          tuple[Ambiguity, ...]
    evidence:             tuple[MatchEvidence, ...]
    normalization_decisions: tuple[str, ...]
    context_reference:    ContextReference | None
    correlation_request:  CorrelationRequest | None
    conditions:           tuple[Condition, ...]
    provider_id:          str
    source_ref:           str | None                  # for re-parse / replay
    parser_version:       str
```

`REQUIREMENT` — Signal Core receives only resolved canonical semantics via
the OUTPUT ADAPTER. The IR contains NO provider-specific tokens, regex
patterns, or symbol aliases.

### 13.3 Single Owner of Parse Outcome

`REQUIREMENT` — the parse outcome has EXACTLY ONE authoritative owner:
`ParseResult.outcome`. `CanonicalParserIR` MUST NOT carry an `outcome`
field. Any API surface that returns a `CanonicalParserIR` without a
`ParseResult` wrapper is forbidden from stating a parse outcome.

Consistency invariant (enforced by Phase 3+ tests):

```text
ParseResult.outcome == derive_outcome(ParseResult.ir)
```

`derive_outcome(ir) -> ParseResultState` is a single pure function that
derives the outcome from the IR contents (unresolved fields, conflicts,
ambiguities) TOGETHER WITH the parser's stage-level decisions of §14 —
grammar violations, media-only / empty / deleted messages, and
unsupported features — which are NOT fields of the IR. It is implemented
in Phase 3+ (engine behaviour), NOT in the Phase 2A contract layer; the
Phase 2A contract is purely structural: `ParseResult.outcome` is the
single owner and `CanonicalParserIR` has no `outcome` field. The outcome
is never stored in the IR and never computed by a second independent
code path that could disagree with `ParseResult.outcome`.

`DESIGN DECISION` — `raw_payload_hash` (SHA-256 of `raw_text`, §5.1) is
a MESSAGE-IDENTITY/DEDUP hash of the raw payload. It is distinct from the
canonical semantic fingerprint (SHA-256 of the canonical snapshot per
`docs/canonical-snapshot-contract.md`). The parser never uses
`raw_payload_hash` as a semantic fingerprint, and never uses the
canonical fingerprint for raw-message dedup; the two are computed from
different inputs for different purposes and must not be conflated.

---

## 14. Failure Model

### 14.1 Six Discrete Outcomes

`REQUIREMENT` —

```text
ParseResultState = PARSED | PARTIAL | AMBIGUOUS | MALFORMED |
                   UNSUPPORTED | NO_SIGNAL
```

| State | Occurs when |
|-------|-------------|
| `PARSED` | All required canonical fields present; no conflicts; no ambiguities. |
| `PARTIAL` | Some fields present; some absent WITHOUT being a grammar violation (multi-message construction, percent-dependent SL/TP, or a direction-only fragment awaiting entry). |
| `AMBIGUOUS` | Multiple valid interpretations; parser cannot choose. |
| `MALFORMED` | Syntax violates the provider's grammar or is structurally invalid (broken range/number, numeric overflow, oversized message, a `required` rule whose extraction target is absent — see §14.2). A missing numeric entry is NOT, by itself, MALFORMED. |
| `UNSUPPORTED` | Syntax valid but the feature is not supported (conditional entry, hedged pairs, OCO, media-only). |
| `NO_SIGNAL` | Not a signal (chat, admin, follow-up-only, deleted message). |

`REQUIREMENT` — never silently reinterpret malformed or ambiguous input.
`DESIGN DECISION` — no confidence scores (same rationale as §7.3 of the
previous revision).

### 14.2 Missing Numeric Entry — Decision Procedure

`REQUIREMENT` — a missing numeric entry is NEVER, by itself, MALFORMED.
Phase 1 permits a MARKET entry with no entry price and requires
`EntryTrigger.UNSPECIFIED` to remain distinct from `EntryTrigger.MARKET`
(Phase 1 §1.5, §3.7.5). The parser applies the following procedure in
order (first matching branch wins). Wherever the procedure says "per
profile", the `ProviderProfile` determines the outcome; the same raw
message may therefore be PARTIAL on one provider and MALFORMED on
another.

1. **Explicit MARKET.** A rule binds an explicit market keyword (e.g.,
   `"BUY MARKET"`): `entry_geometry = MARKET`, `entry_trigger = MARKET`,
   `entry_price = None`. → `PARSED` (if all other required fields are
   present and consistent). MARKET is assigned ONLY from explicit
   provider semantics, never inferred from a missing number.
2. **Direction + numeric price, trigger UNSPECIFIED.** A rule binds
   direction and an entry number but no trigger keyword: geometry per the
   number's form (SINGLE/RANGE/MULTIPLE), `entry_trigger = UNSPECIFIED`.
   → `PARSED`. UNSPECIFIED is NOT promoted to MARKET and NOT treated as
   malformed (§20.2).
3. **Direction only, awaiting fields.** A rule binds direction (and
   possibly instrument) but neither an entry number nor an explicit
   MARKET keyword. If the profile's grammar permits direction-only
   fragments (the profile declares `capabilities.multi_message` and/or a
   rule marks the entry slot as awaitable), → `PARTIAL` with
   `unresolved_fields` containing `ENTRY_GEOMETRY` / `ENTRY_TRIGGER`
   (and `ENTRY`), and evidence `entry_pending`. The raw direction text
   is preserved; nothing is invented.
4. **Provider grammar violation (MALFORMED).** A `required` rule's anchor
   token/keyword matched but its extraction target is absent (e.g., a
   profile whose grammar requires a number after `SL`, and `"SL"`
   appears with no number). → `MALFORMED` with evidence
   `grammar_violation_missing_number`. This is per profile.
5. **Genuinely malformed syntax.** Structural breakage — broken range
   (`"2350-"`), numeric overflow (§15.3), oversized message (§15.3), or
   token-level garbage where the grammar demands a token — → `MALFORMED`
   with the corresponding evidence.

Invariants preserved: no promotion of UNSPECIFIED→MARKET; no invented
entry price; explicit MARKET only from explicit provider semantics;
missing fields remain missing (empty/absent), never defaulted.

---

## 15. Regex Safety Model

### 15.1 Controlled Subsystem

`REQUIREMENT` — regex execution is a controlled subsystem. The parser
does NOT assume arbitrary regex patterns are safe.

### 15.2 Addressed Threats

`REQUIREMENT` — the design addresses:

- catastrophic backtracking;
- pathological input;
- oversized messages;
- repeated numeric tokens;
- Unicode;
- emoji;
- Markdown;
- HTML;
- zero-width characters;
- overlapping matches.

### 15.3 Controls

`REQUIREMENT` — four independent, explicit layers. Only the first three
are inside the pure parser; the fourth is an external availability
backstop (§15.5).

- **Static regex safety (load time; PRIMARY).** A profile validator
  rejects, at PROFILE LOAD TIME (never at parse time), any pattern
  outside the safe subset: nested quantifiers (`(a+)+`, `(a*)*`,
  `(a+)*`); unbounded quantifiers (`*`, `+`) nested inside another
  quantified group or adjacent to an ambiguous alternation that can
  produce exponential backtracking; backreferences; variable-length
  lookbehind. Only patterns that pass the static checker are compiled.
  This is the primary guarantee and it is fully deterministic.
- **Bounded input.** `ProviderProfile.max_message_length` (default 8000
  chars); longer → `MALFORMED` + `message_too_long`. Raw text is NOT
  truncated. Only `\t`, `\n`, `\r` control chars are permitted (§16.2).
- **Bounded numeric / token / candidate / match counts.** Numbers
  exceeding `ProviderProfile.max_numeric_value` (default 1e12) →
  `MALFORMED` + `numeric_overflow`. Per-message numeric token limit
  (default 16 per field, 64 per message) → `MALFORMED` +
  `numeric_list_too_long`. Per-message rule-match limit (default 200) →
  `MALFORMED` + `rule_match_limit_exceeded`. Per-message candidate limit
  (default 256) → `MALFORMED` + `candidate_limit_exceeded`.
- **Runtime timeout guarantee (NARROWED).** See §15.5. The parser does
  NOT promise a hard wall-clock preemption of a running `re` call.

Supporting conventions (unchanged from the prior revision):

- **Precompiled rules**: tokenizer pattern and rule patterns compiled once
  at profile load, never per message.
- **Safe pattern conventions**: single compiled alternation per profile;
  anchored branches; length-bounded numeric captures (`\d{1,12}`);
  no backreferences; no overlapping branches.
- **Deterministic evaluation order**: see §7.3.
- **Overlapping matches**: longer match wins; ties resolved by priority
  then `rule_id`; overlap recorded as evidence.

### 15.4 No New Regex Dependency

`REQUIREMENT` — Python standard-library `re` only. No `regex` library
dependency is added.

### 15.5 Runtime Timeout Guarantee — Narrowed

`DESIGN DECISION` — a hard wall-clock timeout that preempts a RUNNING
`re` match CANNOT be implemented in-process with the standard library:

- `signal.SIGALRM` is POSIX-only, main-thread-only, and unsafe in
  threaded processes;
- a `threading.Thread` cannot be safely killed, so a runaway match
  cannot be reliably aborted;
- `re` exposes no timeout parameter.

The parser therefore does NOT claim a per-regex 50ms / per-message 100ms
hard wall-clock guarantee. That guarantee is REPLACED by the following
deterministic, implementable contract:

1. **Deterministic bounded work (the real guarantee).** With (a) static
   pattern safety, (b) `max_message_length`, and (c) the token/numeric/
   candidate/match-count bounds of §15.3, every regex execution is
   bounded: safe patterns on input ≤ 8000 chars complete in finite,
   statically boundable work. The parser's worst-case cost is a
   documented function of message length and rule count — no unbounded
   backtracking is possible. This holds on ANY hardware,
   deterministically, with no timer.
2. **Per-message cooperative budget (availability control, NOT a
   determinism control).** The INGESTION/correlation layer (Phase 3+),
   OUTSIDE the pure parser, MAY check an elapsed wall-clock budget
   between pipeline stages using `time.monotonic()` and abort the
   overall parse as an infrastructure failure. This is deliberately
   outside the pure parser (the parser itself never reads the clock,
   §4.4) and is explicitly NON-DETERMINISTIC in outcome (the same input
   may be aborted on slow hardware). It is an availability/DoS backstop,
   not a correctness guarantee, and is optional.

With layer (1), a regex timeout is unreachable for validated profiles;
layer (2) exists only to contain a future unvalidated-pattern bug or an
unforeseen algorithmic pathology. `regex_timeout` evidence is therefore
RESERVED for the Phase 3+ supervisor path, not emitted by the pure
parser.

---

## 16. Security Model

### 16.1 Threat Model

`REQUIREMENT` — all provider messages are untrusted. Threats addressed:

- regex DoS (catastrophic backtracking → §15);
- CPU exhaustion (deterministic bounded work, not wall-clock preemption
  → §15.3/§15.5);
- memory exhaustion (message length, token, candidate limits);
- malformed numeric content (overflow, scientific notation, negative
  prices);
- Unicode spoofing (bidi controls, zero-width, combining-mark-only);
- malicious formatting (Markdown/HTML stripping, URLs never followed,
  file references never opened);
- pathological repetition (long same-char runs truncated + flagged).

### 16.2 Untrusted Input Rules

`REQUIREMENT` —

- Reject oversized messages.
- Reject embedded binary (allow only `\t`, `\n`, `\r` control chars).
- Reject zero-width or bidi-control-only content by default.
- Preserve raw text verbatim; never truncate the raw.
- Do not follow URLs; do not open media references.

### 16.3 Provider Impersonation

`DESIGN DECISION` — `provider_name` is set by the ingestion adapter, not
inferred from message text. The parser does not trust message text for
provider identity.

### 16.4 Media-Only and Unopened Media Policy

`REQUIREMENT` — the parser NEVER opens, fetches, decodes, or follows
media references (images, videos, documents) or URLs.
`RawMessage.media_refs` carries `MediaKind` references only.

Decision procedure:

- **Text present and parseable.** Parse the text; `media_refs` are
  recorded in the IR evidence (`media_present`, unopened) and otherwise
  ignored by the parser. Media may later be decoded by the ingestion
  layer, which must feed any media-derived text back through the parser
  as ordinary text.
- **No text (or whitespace-only) but media present.** → `UNSUPPORTED`
  with evidence `media_only_unopened`. The parser cannot extract signal
  semantics from an unopened media payload; it does NOT invent a signal
  and does NOT open the payload.
- **No text and no media.** → `NO_SIGNAL` (empty message).

---

## 17. Test Architecture

### 17.1 Directory Hierarchy

`REQUIREMENT` —

```text
tests/
  parser/
    contract/          # type contracts, immutability, IR shape
    lexical/           # normalization, tokenization, spans
    semantic/          # candidates, rules, resolution, fragments
    adversarial/       # ReDoS, unicode bidi, overflow, repetition
    providers/
      provider_001/
      provider_002/
      provider_003/
```

### 17.2 Per-Provider Fixture Content

`REQUIREMENT` — each provider fixture contains:

- raw input;
- expected candidates;
- expected semantic result;
- expected ambiguity;
- expected action;
- expected context requirements.

### 17.3 Three Providers First

`REQUIREMENT` — test three structurally different example providers
(provider_001 inline comma-separated; provider_002 multiline em-dash;
provider_003 emoji/bitcoin-style) before scaling to 20+.

### 17.4 Contract / Boundary Tests

`DESIGN DECISION` — architectural-boundary test
(`tests/parser/contract/` or `tests/architecture/`) enforces that parser
modules never import Telegram/Discord/broker SDKs. Reserved for Phase 3+.

---

## 18. Performance Strategy

### 18.1 No Invented Latency Guarantees

`REQUIREMENT` — no absolute latency guarantees are invented. Measure
before optimizing.

### 18.2 Benchmark Suites

`REQUIREMENT` — benchmarks for:

- normalization;
- tokenization;
- candidate extraction;
- rule evaluation;
- semantic resolution;
- total parse.

### 18.3 Benchmark Message Classes

`REQUIREMENT` —

- tiny message;
- normal message;
- large message;
- multi-signal message;
- multi-message assembly;
- pathological message.

### 18.4 Hot-Path Discipline

`DESIGN DECISION` — no network, database, synchronous I/O, locks, or
global mutable state in the parse path. Frozen dataclasses; precompiled
patterns; rule lists sorted at load time.

---

## 19. Extensibility Acceptance Test

### 19.1 Architectural Acceptance Test

`REQUIREMENT` — define an acceptance test: adding a new provider with only
a provider profile + rules + fixtures must NOT require modifying the
generic parser engine.

### 19.2 If Modification Is Required

`REQUIREMENT` — if the generic engine must be modified, the design must
identify why (a genuinely new capability) and record it via ADR. This is
the only acceptable reason for engine modification; per-provider hacks are
forbidden.

---

## 20. Example Signals

Synthetic examples representing capability categories; NOT verbatim
provider messages. `INFERENCE`

### 20.1 Simple BUY LIMIT

```text
Input: "BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100"
Outcome: PARSED
Fragments: direction=BUY, instrument=EURUSD, entry_trigger=LIMIT,
           entry_price=1.1000, SL=1.0950, TP=(1.1100)
```

### 20.2 BUY with No Trigger

```text
Input: "BUY 3350 SL 3340 TP 3400"
Outcome: PARSED
Fragments: direction=BUY, entry_trigger=UNSPECIFIED, entry_price=3350,
           SL=3340, TP=(3400)
```

### 20.2a Explicit MARKET (No Entry Price)

```text
Input: "BUY MARKET EURUSD SL 1.0950 TP 1.1100"
Outcome: PARSED
Fragments: direction=BUY, entry_geometry=MARKET, entry_trigger=MARKET,
           entry_price=None, SL=1.0950, TP=(1.1100)
```

### 20.2b Direction Only (Awaiting Entry)

```text
Input: "BUY"  (profile permits direction-only fragments, multi_message)
Outcome: PARTIAL
unresolved_fields: [ENTRY, ENTRY_GEOMETRY, ENTRY_TRIGGER]
Evidence: [entry_pending]
```

The same input on a profile whose grammar REQUIRES an entry when a
direction is present yields MALFORMED with evidence
`grammar_violation_missing_number` (§14.2).

### 20.3 Range Entry

```text
Input: "BUY XAUUSD 2350-2360 SL 2340 TP 2400"
Outcome: PARSED
Fragments: entry_geometry=RANGE, entry_range=(2350, 2360), SL=2340, TP=(2400)
```

### 20.4 Multiple Entry Levels

```text
Input: "SELL NAS100 16200 / 16300 / 16400 SL 16600 TP 15800"
Outcome: PARSED
Fragments: entry_geometry=MULTIPLE, entry_levels=(16400, 16300, 16200),
           SL=16600, TP=(15800)
```

### 20.5 Close Fully

```text
Input: "CLOSE 12345"
Outcome: PARSED (action)
Fragments: instruction_type=CLOSE, correlation_request=TARGET_LAST_SIGNAL
```

### 20.6 Close Half

```text
Input: "CLOSE HALF"
Outcome: PARSED (action)
Fragments: instruction_type=PARTIAL_CLOSE, partial_close_percent=50
```

### 20.7 Close 50% (Explicit Percent)

```text
Input: "CLOSE 50%"
Outcome: PARSED (action)
Fragments: instruction_type=PARTIAL_CLOSE, partial_close_percent=50
```

### 20.8 Profit-Conditioned Close

```text
Input: "CLOSE 30% AT 1.1100"
Outcome: PARSED (action)
Fragments: instruction_type=PARTIAL_CLOSE, partial_close_percent=30,
           condition=(AT_PRICE, 1.1100)
```

### 20.9 Breakeven

```text
Input: "MOVE SL TO BE"
Outcome: PARSED (action)
Fragments: instruction_type=BREAKEVEN
```

### 20.10 Remove SL

```text
Input: "REMOVE SL"
Outcome: PARSED (action)
Fragments: instruction_type=MOVE_SL, remove_sl=True
```

### 20.11 Cancel Pending

```text
Input: "CANCEL PENDING"
Outcome: PARSED (action)
Fragments: instruction_type=CANCEL, cancel_pending=True
```

### 20.12 Trigger Pending

```text
Input: "TRIGGER PENDING NOW"
Outcome: PARSED (action)
Fragments: instruction_type=MODIFY, trigger_pending=True
```

(Open question: `TRIGGER_PENDING` as its own `InstructionType` — see §24.)

### 20.13 Change SL (Follow-Up)

```text
Input: "SL 3320"
Outcome: NO_SIGNAL
Evidence: [follow_up_only]
CorrelationRequest: TARGET_LAST_SIGNAL (fragment: instruction_type=MOVE_SL,
                    move_sl_to=3320)
```

vs.

```text
Input: "EURUSD SL 3320"
Outcome: PARSED (action)
Fragments: instruction_type=MOVE_SL, move_sl_to=3320
```

### 20.14 Change TP

```text
Input: "TP 1.1150 / 1.1200"
Outcome: PARSED (action)
Fragments: instruction_type=MOVE_TP, move_tp_to=(1.1150, 1.1200)
```

### 20.15 Change Entry

```text
Input: "CHANGE ENTRY TO 1.1020"
Outcome: PARSED (action)
Fragments: instruction_type=MODIFY, entry_price=1.1020
```

### 20.16 Keyword-Conditioned Extraction

```text
Input: "if price reaches 1.1050, BUY LIMIT 1.1060 SL 1.1000 TP 1.1100"
Outcome: AMBIGUOUS or UNSUPPORTED
Evidence: [unsupported_feature:conditional_entry]
```

### 20.17 Edited Original

```text
MessageEvent: EDIT
Input (raw, latest): "BUY EURUSD @ 1.1010 SL 1.0960 TP 1.1100"
Outcome: PARSED
EditDelta: entry_price 1.1000 -> 1.1010, SL 1.0950 -> 1.0960
```

### 20.18 Deleted Original

```text
MessageEvent: DELETE
Input (raw, last known): "BUY EURUSD @ 1.1000 ..."
Outcome: NO_SIGNAL
Evidence: [message_deleted]
CorrelationRequest: DELETE_APPLY
```

### 20.19 Media-Only (Unopened)

```text
Input: raw_text = "" (or whitespace-only), media_refs = (IMAGE,)
Outcome: UNSUPPORTED
Evidence: [media_only_unopened]
```

The parser does not open the media payload and does not invent a signal
(§16.4).

---

## 21. Example Provider Variations

Synthetic; NOT verbatim provider messages. `INFERENCE`

### 21.1 Provider Alpha (Inline, Comma-Separated)

```text
"BUY, EURUSD, 1.1000, SL 1.0950, TP 1.1100"
```

### 21.2 Provider Bravo (Multiline, Em-Dash)

```text
BUY EURUSD
ENTRY 1.1000
SL — 1.0950
TP — 1.1100
```

### 21.3 Provider Charlie (Bitcoin-Style, No Decimals)

```text
LONG BTC 60000 SL 58000 TP 65000
```

### 21.4 Provider Delta (Emoji-Heavy)

```text
🟢 BUY #EURUSD
🎯 1.1000
🛑 1.0950
💰 1.1100
```

### 21.5 Provider Echo (Conditional / If-Then)

```text
IF price >= 1.1100 THEN BUY STOP 1.1110 SL 1.1050 TP 1.1200
```

### 21.6 Provider Foxtrot (Percent-Only SL/TP)

```text
BUY EURUSD @ 1.1000 SL 0.5% TP 1.0%
```

### 21.7 Provider Golf (Multi-Line, Numbered Levels)

```text
SCALP LONG
1) 3350
2) 3340
3) 3330
SL 3300
TP 3400
```

### 21.8 Provider Hotel (Pending Order Style)

```text
PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100
```

### 21.9 Provider India (Reverse Direction Keyword)

```text
REVERSE TO SELL @ 1.1000 SL 1.1050 TP 1.0900
```

### 21.10 Provider Juliett (German Decimal Format)

```text
KAUF EURUSD 1,1000 SL 1,0950 TP 1,1100
```

---

## 22. Extension Mechanism

### 22.1 Adding a New Provider

`REQUIREMENT` —

1. Write a `ProviderProfile` (TOML/dict) with `ProviderCapabilities` and
   `RuleSet`.
2. Add fixtures under `tests/parser/providers/<provider>/`.
3. Run the parser test suite.
4. The parser Python code is unchanged (extensibility acceptance test,
   §19).

### 22.2 Adding a New Rule Category

`DESIGN DECISION` — requires a generic parser code change + ADR; existing
providers keep working.

### 22.3 Adding a New Canonical Field

`DESIGN DECISION` — new IR field defaults to `None`/empty for existing
providers; OUTPUT ADAPTER integrates it into the canonical snapshot
projection per `docs/canonical-snapshot-contract.md`.

### 22.4 Adding a New Parse Result State

`REQUIREMENT` — forbidden in steady state. The six states are closed;
adding a seventh requires an ADR and a backward-compatibility strategy.

---

## 23. Open Questions

1. `OPEN QUESTION` — `TRIGGER_PENDING`: own `InstructionType` or
   `MODIFY` + flag? Deferred.
2. `OPEN QUESTION` — percent-dependent SL/TP before entry price known
   (design: `PARTIAL` + `percent_dependent_on_entry`).
3. `OPEN QUESTION` — conditional / if-then entries (design:
   `UNSUPPORTED` + future rule category).
4. `OPEN QUESTION` — multi-instrument signals.
5. `OPEN QUESTION` — hedged pair signals.
6. `OPEN QUESTION` — reverse direction identity policy (new signal vs
   update existing).
7. `OPEN QUESTION` — exact edit delta semantics (fingerprint comparison
   policy) — deferred to Phase 3+.
8. `OPEN QUESTION` — provider symbol mapping ("GOLD" → XAUUSD) — per
   Profile `symbol_aliases`; no global table.
9. `OPEN QUESTION` — profile versioning / hot-reload.

Provider-specific realizations of the capability categories are, until a
provider's actual format is supplied:

```text
UNKNOWN — REQUIRES PROVIDER EVIDENCE
```

---

## 24. ADRs Required

All ADRs stored in `docs/adr/000N-<slug>.md`, in the standard ADR
template (Status, Context, Decision, Consequences):

1. `0001-parser-stage-architecture.md` — compiler-like pipeline
   decomposition (§4-§5).
2. `0002-rule-decomposition-strategy.md` — declarative `ProviderRule`
   primitives and `RuleSet` inheritance (§7, §12).
3. `0003-message-model-without-ingestion.md` — `RawMessage` +
   `MessageMetadata`; no ingestion imports (§5, §9).
4. `0004-canonical-ir-surface.md` — `CanonicalParserIR` +
   `ParseResult`; provider-syntax-free surface (§13).
5. `0005-parse-result-states.md` — six discrete states, no confidence
   (§14).
6. `0006-correlation-contract.md` — five-layer separation;
   `CorrelationRequest`; parser does not correlate (§9-§11).
7. `0007-regex-safety-model.md` — bounded regex subsystem; narrowed
   runtime-timeout guarantee (§15).
8. `0008-candidate-graph.md` — competing candidates; four resolver
   relationships (§5-§6).
9. `0009-action-semantics.md` — actions as semantic instructions;
   conditions recorded, not evaluated (§8).
10. `0010-message-events-edit-delta.md` — `MessageEvent` enum;
    `EditDelta`; message vs Signal lifecycle (§9).
11. `0011-provider-capabilities-vs-rules.md` — capabilities vs rules;
    extensibility acceptance test (§12, §19).
12. `0012-source-span-mapping.md` — deterministic normalized ↔ raw
    offset mapping; spans always traceable to raw characters
    (§5.3, §5.5.1, §13.1).

---

## 25. Implementation Sequence

Reconciliation note (2026-09-05): steps 1–4 and 6–9 were executed as
Phase 2A–2F and adopted by the owner; step 5 (`packages/parser/output_adapter.py`)
was implemented during the 2026-09-05 reconciliation. Step 10 (Phase 3.1)
has NOT been started and requires explicit approval.

1. Create `packages/parser/` skeleton.
2. Create `packages/parser/types.py` with the 21 mandatory concepts and
   every supporting type in the authoritative registry (§26): enums and
   value objects `MessageEvent`, `MediaKind`, `TokenCategory`,
   `CandidateSlot`, `FragmentState`, `ConditionKind`, `ConflictKind`,
   `AmbiguityKind`, `ContextReferenceKind`, `ContextRequirement`,
   `CorrelationRequestKind`, `MatcherKind`, `ScopeKind`,
   `SemanticTarget`, `OccurrenceSelection`, `Constraint`,
   `ReplyRequirement`, `EditBehavior`, `DeleteBehavior`,
   `FollowUpBehavior`, `ParseResultState`, and the value objects
   `SourceMap`, `SourceSpan`, `MatcherSpec`, `ScopeSpec`, `Anchor`,
   `Condition`.
3. Create `packages/parser/pipeline.py` (pure stage functions).
4. Create `packages/parser/safety.py` (static pattern validator,
   message-length/numeric/token/candidate/match-count bounds, profile
   validation — no wall-clock timeout in the pure parser, §15).
5. Create `packages/parser/output_adapter.py` (IR → Signal /
   SignalInstruction / non-signal).
6. Create `packages/parser_profiles/data/` (common + domain profiles).
7. Create `tests/parser/` hierarchy and boundary test.
8. Populate three structurally different provider fixtures first, then
   scale.
9. Run ruff, mypy, pytest, diff inspection.
10. Begin Phase 3.1 only after explicit approval.

---

## 26. Supporting Type Registry (Authoritative)

`REQUIREMENT` — every enum and value object referenced anywhere in this
document is defined exactly here. No type may be referenced by the Phase
2 design without a definition in this registry. Where a type already
exists in Phase 1 (`packages.signal_core`), it is listed as IMPORTED; the
parser introduces no new member to any Phase 1 enum.

### 26.1 Enums

| Enum | Members | Origin |
|------|---------|--------|
| `ParseResultState` | PARSED, PARTIAL, AMBIGUOUS, MALFORMED, UNSUPPORTED, NO_SIGNAL (+ `MULTI_SIGNAL`, added by ADR 0013 for multi-block messages — the documented seventh state and its backward-compatibility contract are owned by that ADR) | Phase 2 |
| `MessageEvent` | CREATE, EDIT, DELETE, FOLLOW_UP | Phase 2 |
| `MediaKind` | IMAGE, VIDEO, DOCUMENT, NONE | Phase 2 |
| `TokenCategory` | NUMBER, KEYWORD, SYMBOL, PUNCT, WHITESPACE, TEXT, EMOJI | Phase 2 |
| `CandidateSlot` | DIRECTION, INSTRUMENT, ENTRY, ENTRY_GEOMETRY, ENTRY_TRIGGER, SL, TP, ACTION, CONDITION, METADATA, PRICE, RANGE | Phase 2 |
| `FragmentState` | RESOLVED, UNRESOLVED, CONDITIONAL | Phase 2 |
| `ConditionKind` | IN_PROFIT, AT_PRICE, KEYWORD_PRESENT, NONE | Phase 2 |
| `ConflictKind` | CONFLICTING | Phase 2 |
| `AmbiguityKind` | AMBIGUOUS_TRIGGER, AMBIGUOUS_RANGE, AMBIGUOUS_PERCENT | Phase 2 |
| `ContextReferenceKind` | REPLY, QUOTE, LAST_SIGNAL, EDITED_ORIGINAL, NONE | Phase 2 |
| `ContextRequirement` | NONE, REPLY_REQUIRED, CONTEXT_REQUIRED, LAST_SIGNAL | Phase 2 |
| `CorrelationRequestKind` | TARGET_LAST_SIGNAL, TARGET_REPLIED_SIGNAL, MULTI_MESSAGE_APPEND, EDIT_APPLY, DELETE_APPLY, NONE | Phase 2 |
| `MatcherKind` | LITERAL, REGEX, TOKEN_SEQUENCE, SYMBOL, ALIAS, NUMBER, PRICE, PRICE_RANGE | Phase 2 |
| `ScopeKind` | WHOLE_MESSAGE, LINE, SECTION, AFTER_TOKEN, BEFORE_TOKEN, BETWEEN_ANCHORS, REPLY, QUOTED_MESSAGE | Phase 2 |
| `SemanticTarget` | DIRECTION, INSTRUMENT, ENTRY, ENTRY_GEOMETRY, ENTRY_TRIGGER, SL, TP, ACTION, CONDITION, METADATA | Phase 2 |
| `OccurrenceSelection` | FIRST, LAST, NTH, ALL | Phase 2 |
| `Constraint` | REQUIRES, FORBIDS, REQUIRED, REQUIRES_REPLY, REQUIRES_CONTEXT, MUTUALLY_EXCLUSIVE, REPEATABLE, UNIQUENESS | Phase 2 |
| `ReplyRequirement` | NONE, REQUIRED, OPTIONAL | Phase 2 |
| `EditBehavior` | REPARSE_DELTA, IGNORE | Phase 2 |
| `DeleteBehavior` | CANCEL_TARGET, IGNORE | Phase 2 |
| `FollowUpBehavior` | TARGET_LAST_SIGNAL, IGNORE | Phase 2 |
| `TradeDirection` | BUY, SELL | IMPORTED (Phase 1) |
| `EntryGeometry` | MARKET, SINGLE, RANGE, MULTIPLE | IMPORTED (Phase 1) |
| `EntryTrigger` | MARKET, LIMIT, STOP, UNSPECIFIED | IMPORTED (Phase 1) |
| `LifecycleState` | DRAFT, ACTIVE, CANCELLED, EXPIRED, ARCHIVED | IMPORTED (Phase 1) |
| `SignalStatus` | PARTIAL, COMPLETE, AMBIGUOUS | IMPORTED (Phase 1) |
| `EventType` | Phase 1 §3.11; NOT extended | IMPORTED (Phase 1) |
| `InstructionType` | OPEN, MODIFY, CANCEL, CLOSE, PARTIAL_CLOSE, MOVE_SL, MOVE_TP, BREAKEVEN, TRAIL, SCALE_IN, SCALE_OUT, REVERSE | IMPORTED (Phase 1) |
| `SourceType` | TELEGRAM, DISCORD, MANUAL, API | IMPORTED (Phase 1) |
| `AssetClass` | FOREX, CRYPTO, STOCK, INDEX, COMMODITY, BOND, ETF, OTHER | IMPORTED (Phase 1) |

### 26.2 Value Objects / Dataclasses

Phase 2 types (all `@dataclass(frozen=True, slots=True)`):

| Type | Fields | Origin |
|------|--------|--------|
| `RawMessage` | `raw_text: str`, `media_refs: tuple[MediaKind, ...]`, `raw_payload_hash: str` | Phase 2 |
| `MessageMetadata` | `provider_name: str`, `source_type: SourceType`, `source_reference: str | None`, `timestamp_utc: datetime`, `message_event: MessageEvent`, `reply_to: ContextReference | None`, `provenance_extra: tuple[tuple[str, object], ...]` | Phase 2 |
| `NormalizedMessage` | `normalized_text: str`, `source_map: SourceMap`, `normalization_decisions: tuple[str, ...]` | Phase 2 |
| `SourceMap` | `char_ranges: tuple[tuple[int, int], ...]`, `deleted_ranges: tuple[tuple[int, int, str], ...]` | Phase 2 |
| `SourceSpan` | `start: int`, `end: int`, `source_reference: str | None` | Phase 2 |
| `Token` | `category: TokenCategory`, `text: str`, `source_span: SourceSpan` | Phase 2 |
| `Candidate` | `slot: CandidateSlot`, `value: object`, `source_span: SourceSpan`, `provenance: tuple[MatchEvidence, ...]` | Phase 2 |
| `CandidateGraph` | `by_slot: tuple[tuple[CandidateSlot, tuple[Candidate, ...]], ...]` | Phase 2 |
| `MatchEvidence` | `kind: str`, `rule_id: str | None`, `span: SourceSpan | None`, `snippet: str | None`, `fields: tuple[tuple[str, object], ...]`, `reason: str | None` | Phase 2 |
| `RuleMatch` | `rule_id: str`, `category: str`, `span: SourceSpan`, `bindings: tuple[tuple[str, Candidate], ...]`, `evidence: tuple[MatchEvidence, ...]` | Phase 2 |
| `Conflict` | `kind: ConflictKind`, `slot: CandidateSlot`, `involved: tuple[Candidate, ...]`, `spans: tuple[SourceSpan, ...]`, `reason: str` | Phase 2 |
| `Ambiguity` | `kind: AmbiguityKind`, `slot: CandidateSlot | None`, `candidates: tuple[Candidate, ...]`, `spans: tuple[SourceSpan, ...]`, `reason: str` | Phase 2 |
| `ParsedFragment` | `slot: CandidateSlot`, `value: object`, `state: FragmentState`, `condition: tuple[Condition, ...]`, `evidence: tuple[MatchEvidence, ...]`, `context_requirement: ContextRequirement` | Phase 2 |
| `Condition` | `kind: ConditionKind`, `params: tuple[tuple[str, object], ...]` | Phase 2 |
| `CanonicalParserIR` | `candidates`, `unresolved_fields`, `fragments`, `conflicts`, `ambiguities`, `evidence`, `normalization_decisions`, `context_reference`, `correlation_request`, `conditions`, `provider_id`, `source_ref`, `parser_version` (§13.2; NO `outcome` field) | Phase 2 |
| `ParseResult` | `outcome: ParseResultState`, `ir: CanonicalParserIR` | Phase 2 |
| `ProviderProfile` | `provider_name`, `capabilities`, `rule_set`, `symbol_aliases`, `tokenizer_pattern`, `field_separators`, `multi_value_separators`, `decimal_format`, `range_patterns`, `multiline_mode`, `reply_requirement`, `edit_behavior`, `delete_behavior`, `follow_up_behavior`, `max_message_length`, `max_numeric_value`, `version` (§5.15) | Phase 2 |
| `ProviderCapabilities` | 19 boolean flags (§5.16) | Phase 2 |
| `ProviderRule` | `id`, `category`, `matcher: MatcherSpec`, `scope: ScopeSpec`, `constraints: tuple[Constraint, ...]`, `target: SemanticTarget`, `priority: int`, `occurrence: OccurrenceSelection` (§7.2) | Phase 2 |
| `MatcherSpec` | `kind: MatcherKind`, `params: tuple[tuple[str, object], ...]` | Phase 2 |
| `ScopeSpec` | `kind: ScopeKind`, `anchors: tuple[Anchor, ...]` (anchor = token/keyword reference) | Phase 2 |
| `Anchor` | `text: str` (the referenced token/keyword text, e.g. `"SL"` for an `AFTER_TOKEN` scope) | Phase 2 |
| `RuleSet` | `rules: tuple[ProviderRule, ...]`, `parent: str | None`, `overrides: tuple[tuple[str, str], ...]`, `exclusions: tuple[str, ...]` (§5.18) | Phase 2 |
| `ContextReference` | `provider_name: str`, `source_reference: str | None`, `signal_identity: SignalIdentity | None`, `kind: ContextReferenceKind` | Phase 2 |
| `CorrelationRequest` | `kind: CorrelationRequestKind`, `target: ContextReference | None`, `fragments: tuple[ParsedFragment, ...]` | Phase 2 |
| `EditDelta` | `added: tuple[ParsedFragment, ...]`, `changed: tuple[tuple[ParsedFragment, ParsedFragment], ...]`, `removed: tuple[ParsedFragment, ...]`, `unchanged: tuple[ParsedFragment, ...]` | Phase 2 |

Imported Phase 1 types (NOT redefined by the parser):

| Type | Origin |
|------|--------|
| `Price`, `PriceRange`, `Instrument`, `ProviderSource`, `SourceIdentity` | IMPORTED (value objects) |
| `SignalIdentity`, `Signal`, `SignalRevision`, `SignalEvent`, `SignalInstruction` | IMPORTED (domain) |
| `canonical_fingerprint`, `ALLOWED_SNAPSHOT_TYPES` | IMPORTED (contract) |

### 26.3 Completeness Rule

`REQUIREMENT` — Phase 3+ implementation MUST define exactly these types
with exactly these fields/members (plus the Phase 1 imports). A Phase 3+
consistency test verifies that (a) every type name appearing in this
design document resolves to a registry entry, and (b) every registry
entry is implemented with the declared fields/members and no extra
undocumented ones.

---

## Cross-Reference: Phase 1 / 1.1 Invariants Preserved

- The IR conforms to `ALLOWED_SNAPSHOT_TYPES` when serialized to a
  `canonical_snapshot`.
- The OUTPUT ADAPTER integrates with `Signal`, `SignalInstruction`,
  `SignalRevision`, `SignalEvent` without modifying them.
- The parser never introduces new `EventType`, `InstructionType`,
  `LifecycleState`, `EntryGeometry`, or `EntryTrigger` members.
- The parser never reintroduces `MODIFIED` as a `LifecycleState`.
- The parser never defaults `UNSPECIFIED` to `MARKET`.
- A missing numeric entry is never, by itself, `MALFORMED` (§14.2); the
  parser never invents prices, directions, or TP/SL values.
- The parse outcome has exactly one owner: `ParseResult.outcome`; the
  `CanonicalParserIR` carries no outcome (§13.3).
- Every span is a raw-text `SourceSpan` derived through the `SourceMap`
  projection; spans always trace back to the exact original raw
  characters (§5.5.1).
- Media references are never opened; media-only messages are
  `UNSUPPORTED`, never a fabricated signal (§16.4).
- The parser preserves raw text and evidence.
- The parser is pure (no I/O, no global state, no time, no randomness).
- The parser does not evaluate broker/account state; it represents
  conditions only.

---

## Phase 2 Design: READY FOR REVIEW

This document is the Phase 2 design. It is not implemented. The user must
explicitly approve the design before Phase 3+ implementation begins. Per
`docs/phase-status.md` maintenance rule, the transition requires:

1. Explicit user instruction to begin Phase 3.
2. Updated `docs/phase-status.md` (Phase 2 design APPROVED; Phase 3 IN
   PROGRESS).
3. ADRs reviewed and accepted.
4. Fixture catalog reviewed and approved.

Until those conditions are met, no Phase 3 implementation may begin.
