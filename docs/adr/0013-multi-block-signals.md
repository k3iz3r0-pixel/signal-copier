# ADR 0013 — Multi-Block Signal Messages

- Status: Accepted (Phase 2E — implemented under explicit owner
  instruction; adopted retroactively by the owner's Phase 2A–2F adoption
  decision of 2026-09-05; see "Phase 2E audit deviations" for the as-built
  contract)
- Date: 2026-09-05 (design); 2026-09-05 (Phase 2E implementation); 2026-09-05 (adoption)
- Deciders: Architect (proposal); Owner (adoption decision 2026-09-05)
- Primary evidence: `docs/corpus/real-messages.md` M19, M20
- Related: ADR 0003 (message model), ADR 0008 (candidate graph),
  ADR 0010 (message events), ADR 0012 (source-span mapping),
  design §5.14 (ParseResult), §10 (correlation separation),
  §11 (multi-signal/multi-message), §13 (IR preservation)

## Context (real corpus)

M19 (lines 215-247) contains FOUR independent order blocks — the same two
US30 stop orders duplicated across two broker data feeds:

```text
Instrument: US30
Cronos Markets data:
SELL STOP / Entry: 53071 / SL: 53241 / TP: 52995
BUY STOP  / Entry: 53238 / SL: 53068 / TP: 53314
⸻
Funding Dynasty data:
SELL STOP / Entry: 53071 / SL: 53241 / TP: 52995   (identical copy)
BUY STOP  / Entry: 53238 / SL: 53068 / TP: 53314   (identical copy)
```

M20 (lines 251-267) mixes lifecycle events and actions with two new
signal blocks: "The sell stop order was triggered." (EVENT), "Delete the
buy stop order." (ACTION), "I've placed a new buy stop:" (NEW_SIGNAL ×2,
identical copies).

Today's single-signal IR cannot represent these messages. The engine's
current behavior is honest but lossy: M19 parses as MALFORMED with
DIRECTION [SELL, BUY] and SL [53241, 53068] conflicts preserved (verified
in Phase 2C probes); M20 mixes actions and new signals in one conflict
set. No silent merging occurs — but the two distinct logical signals are
also not separately actionable, and duplicated feed copies are not
distinguishable from genuinely distinct signals.

## Requirements (owner mandate, Phase 2D)

1. Preserve block boundaries.
2. Preserve raw source spans (global SourceMap; per-block projections).
3. Prevent silent merging — fragments never cross block boundaries.
4. Allow multiple independent signals in one message.
5. Preserve per-block candidate provenance.
6. Remain compatible with `CandidateGraph`.
7. Distinguish duplicated provider-feed blocks from genuinely distinct
   signals.
8. Support future correlation without implementing correlation now.

## Proposed contract shape (additive; nothing existing is broken)

### 1. Segmentation layer (pre-rule, post-tokenize)

A deterministic, pure segmentation of the normalized text into blocks:

```text
MessageBlock:
  index:            int                     # 0-based, message order
  norm_span:        (start, end)            # normalized offsets
  raw_span:         SourceSpan              # via the existing SourceMap
  separator_kind:   BLANK_LINE | DIVIDER_RULE | HEADER_MARKER
```

Segmentation uses only mechanical boundaries (blank-line runs, divider
rules such as `⸻`/`----`, header markers). It is content-agnostic: no
keyword classification happens in the separator, so segmentation cannot
invent semantics. Single-block messages degenerate to one block
(index 0, whole message) — the current behavior, exactly preserved.

### 2. Per-block evaluation, one CandidateGraph per block

The existing tokenizer, normalizer, rule engine, and CandidateGraph are
REUSED unchanged, instantiated per block:

```text
BlockParse:
  block:              MessageBlock
  graph:              CandidateGraph      # candidates scoped to the block
  ir:                 CanonicalParserIR   # per-block, current shape
  outcome:            ParseResultState    # per block (single owner rule)
  violations:         tuple[_Violation]   # per block
  evidence_block_ref: every MatchEvidence in this block additionally
                      carries block_index (see provenance below)
```

Value zones, claims (`owned`/`global_claims`), and core adjacency are
computed per block, which structurally prevents cross-block capture:
a number in block 2 can never satisfy a rule anchored in block 1. No
fragments, conflicts, or ambiguities ever cross a block boundary —
silent merging is impossible by construction, not by convention.

### 3. Result shape (the one true contract change)

`ParseResult` gains ONE additive optional field (default preserves all
current behavior):

```text
ParseResult:
  outcome: ParseResultState          # existing single-owner field
  ir:      CanonicalParserIR         # existing; = blocks[0].ir when
                                     # len(blocks) <= 1, else the
                                     # deterministic first SIGNAL block
                                     # or an empty IR — see §5
  blocks:  tuple[BlockParse, ...] | None = None   # NEW; None = pre-2E
```

`RawMessage`, `Token`, `CandidateGraph`, `ProviderRule`,
`CanonicalParserIR`, `MatchEvidence`, `ParseResultState` are unchanged.
`MessageMetadata` may gain `block_count` for audit only (optional).

### 4. Per-block provenance

Every `MatchEvidence` in a block-scoped graph carries `block_index` (one
new optional int field, default None = single-block legacy). Raw spans
remain the existing global `SourceSpan` values (the SourceMap is never
re-based), so every fragment remains traceable to the exact raw text.

### 5. Outcome rule (deterministic, documented)

- All blocks NO_SIGNAL/empty → message NO_SIGNAL.
- Exactly one block yields an executable signal/action → that block's
  outcome; `ir` is that block's IR (backward-compatible single-signal
  semantics).
- More than one block yields executable content → message outcome
  MULTI_SIGNAL (verified: `ParseResultState` currently has NO such
  member — PARSED/PARTIAL/AMBIGUOUS/MALFORMED/UNSUPPORTED/NO_SIGNAL —
  so this is the one new enum member this ADR requests) and `ir` is
  explicitly EMPTY; consumers MUST read `blocks`. This is the
  anti-merge rule: the parser refuses to pick one signal silently.
- Any block MALFORMED/AMBIGUOUS → message outcome escalates to that
  state (conflicts preserved per block).

### 6. Duplicate-feed detection (fingerprinting, no correlation)

A deterministic per-block payload fingerprint:

```text
fingerprint = hash(
  direction, instrument, trigger,
  entry values (exact Price/PriceRange),
  sl, tp tuple, action
)
```

Blocks with equal fingerprints are marked `duplicate_of: block_index`
(same logical signal posted to two feeds — M19: 4 blocks → 2 logical
signals + 2 duplicate copies). Blocks with distinct fingerprints are
independent signals (never collapsed). Fingerprinting is comparison
only — it does not decide execution; correlation (§10) consumes it.

### 7. Correlation support without correlation

Each BlockParse carries its own optional `CorrelationRequest` and
`ContextReference` (existing types). The correlation layer (Phase 3+)
receives block-scoped requests plus the duplicate grouping; the parser
still performs no identity resolution (ADR 0010 boundary preserved).

## M19 / M20 traceability

- M19 → 4 blocks → fingerprints {SELL-STOP-53071…} ×2 equal, {BUY-STOP-
  53238…} ×2 equal → 2 logical signals, 2 duplicate_of links; message
  MULTI_SIGNAL; nothing merged.
- M20 → blocks [EVENT(trigger)] [ACTION(delete/cancel)] [NEW_SIGNAL ×2]
  → actions and signals remain in their own blocks (today they collide
  in one conflict set); the two new-signal blocks dedupe by fingerprint.

## Explicit non-goals

- No multi-MESSAGE reconstruction (separate messages are never joined —
  unchanged).
- No cross-block context inference (a direction in block 1 never
  qualifies an entry in block 2).
- No REVERSE, percent-only SL/TP, conditional execution, or locale
  decimals (unchanged prohibitions).
- No correlation logic (Phase 3+).

## Required approvals before implementation

1. ParseResult.blocks additive field (Phase 2A/§5.14 contract change —
   explicit owner approval; the ONLY breaking-surface item).
2. ParseResultState member for multi-signal outcome (verify existing
   members; add only if absent).
3. MatchEvidence.block_index optional field.
4. Engine sequencing change (per-block evaluation loop).

Until approved: M19/M20 remain honest-conflict messages under the
current contracts (verified behavior, documented in Phase 2C).

## Phase 2E audit deviations (as-built contract)

The Phase 2D proposal was audited against the real corpus and the engine
before implementation. The following deviations are evidence-backed and
supersede the corresponding proposal text:

1. **Blank lines are NOT unconditional separators.** The proposal listed
   blank-line runs as boundaries. Corpus audit shows ordinary signals are
   full of blank lines (M1 closed-event, M2 ticket blocks, M3 weekly
   report). Blank-line boundaries are active ONLY in sectioned mode (the
   message contains at least one declared divider). Single newlines are
   ordinary intra-block whitespace.
2. **Dividers are profile-declared data, not engine constants.** The
   proposal's "⸻/----" example is wrong: M2 uses
   `----------{ NEW }----------` and `---------------------------` as
   decoration, so ASCII dash rules can never be dividers. The divider set
   is `ProviderProfile.section_dividers` (validated at load; whitespace-
   only rejected because dividers match whitespace-collapsed normalized
   text). Default is empty ⇒ providers 001-017 are PROVABLY on the legacy
   single-unit path for every input, not just current fixtures.
3. **HEADER_MARKER separator kind dropped.** M19's feed headers sit
   inside sections; treating `X:`-lines as boundaries would be semantic.
   Headers merge with the following content block when only single
   newlines separate them (real M19/M20 behavior).
4. **MatchEvidence.block_index NOT implemented.** Per-block IRs scope all
   provenance by containment; spans stay global (ADR 0012). A flat
   cross-block evidence surface would be unconsumed speculative surface;
   if Phase 3 correlation needs it, it is one additive optional field.
5. **Fingerprint is a structured tuple, not a cryptographic hash.**
   Within-message comparison only (equality of
   (slot, value) pairs over DIRECTION, INSTRUMENT, ENTRY_TRIGGER, ENTRY,
   SL, TP, ACTION). Fully inspectable, collision-free, no cross-message
   dedup semantics implied.
6. **BlockParse does not expose the CandidateGraph.** The engine-internal
   graph stays internal, mirroring the whole-message surface (where the
   graph never reaches ParseResult); per-block `ir.candidates` carries
   winners plus PRICE/RANGE reference candidates, exactly as today.
7. **Real M19 yields 9 blocks** (proposal sketched 4): intro ×2,
   disclaimer ×2, `Instrument: US30`, `Cronos Markets data:` + SELL
   order (single newline), BUY order, `Funding Dynasty data:` + SELL
   order, BUY order → 4 PARSED blocks with duplicate_of links (7→5,
   8→6) and message MULTI_SIGNAL. The "4 blocks" sketch was
   illustrative, not normative.
8. **Real M20 escalates to MALFORMED**, not MULTI_SIGNAL: its
   consecutive narrative lines ("The sell stop order was triggered." /
   "Delete the buy stop order.") share one block (single newline) and
   carry SELL+BUY → block-local DIRECTION conflict preserved and
   escalated (§7 safety: conflicting directions refuse execution). The
   two new-signal blocks still parse separately with duplicate_of links.
9. **`multi_signal` capability remains declarative.** Aggregation does
   not consult it; enforcement (e.g. ≥2 executable blocks under
   multi_signal=False ⇒ UNSUPPORTED) is a future owner decision.
10. **§15.3 structural bounds stay message-level.** Tokenize violations
    (e.g. digit-run overflow) reject the whole message before block
    evaluation (blocks=None). Extract/evaluate bounds apply per block.

Implemented contract surface (Phase 2E):

- `ParseResultState.MULTI_SIGNAL` (the one new enum member).
- `MessageBlock` (index, norm bounds, raw bounds, separator kind),
  `BlockParse` (block, outcome, ir, duplicate_of),
  `ParseResult.blocks: tuple[BlockParse, ...] | None = None` (None =
  legacy single-unit shape; populated only for ≥2-block messages).
- `ProviderProfile.section_dividers: tuple[str, ...] = ()`.
- Engine: `_segment_blocks` (mechanical, pure), per-block reuse of
  extract/evaluate/resolve through the unit core extracted verbatim from
  the former `build_parse_result` body (single-unit path byte-identical),
  `_aggregate_block_results` (escalation order MALFORMED > UNSUPPORTED >
  AMBIGUOUS; 1 PARSED block → its IR promoted; ≥2 → MULTI_SIGNAL with
  fragment-free aggregate IR; 0 → PARTIAL/NO_SIGNAL).
