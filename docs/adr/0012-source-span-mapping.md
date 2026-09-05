# ADR 0012 — Raw ↔ Normalized Source-Span Mapping

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §5.3, §5.5.1, §13.1

## Context

Tokens are produced from `NormalizedMessage.normalized_text`, but every
`SourceSpan` is required to point into `raw_text`. Normalization (NFKC
Unicode normalization, whitespace collapsing, Markdown/HTML stripping,
zero-width removal, separator canonicalization) changes offsets, so a
normalized offset can never be used directly as a raw offset. Without an
explicit mapping, spans become either wrong or untraceable, which breaks
the end-to-end auditability requirement of the parser.

The prior revision only said "preserve spans"; it did not define how
normalized offsets map back to raw characters. This ADR makes the
mapping an explicit, deterministic contract.

## Decision

Define `SourceMap`, a frozen value object carried by
`NormalizedMessage`:

```text
@dataclass(frozen=True, slots=True)
class SourceMap:
    char_ranges:     tuple[tuple[int, int], ...]      # len == len(normalized_text);
                                                     # entry i = (raw_start, raw_end)
                                                     # of the raw chars that produced
                                                     # normalized char i
    deleted_ranges:  tuple[tuple[int, int, str], ...] # (raw_start, raw_end, op_name)
                                                     # raw ranges removed by a named
                                                     # normalization op
```

The mapping is built by a FIXED-order pipeline of pure
`(text, SourceMap) -> (text', SourceMap')` steps:

1. strip zero-width / bidi-control characters (deleted ranges recorded);
2. NFKC Unicode normalization (character-granular rebuild);
3. Markdown/HTML syntax stripping (per Profile);
4. whitespace collapsing (one canonical space per run);
5. separator canonicalization (per Profile).

Projection contract:

```text
raw_span_for(norm_start, norm_end) =
    (char_ranges[norm_start][0], char_ranges[norm_end - 1][1])
```

Every `SourceSpan` in the parser output is a raw span computed by this
projection. Normalization never reorders characters (bidi is a rendering
concern; the parser removes/rejects bidi controls). Every raw offset is
accounted for exactly once: either by a `char_ranges` source range or by
a `deleted_ranges` entry.

## Consequences

Positive:

- Every candidate / rule / evidence span is traceable to the exact
  original raw characters, deterministically.
- The mapping is total and pure (no ambiguity, no randomness).
- `SourceMap` is pipeline-internal; downstream types carry only raw
  spans, so the IR stays lean and replay-friendly.

Negative:

- Character-granular mapping costs O(n) memory (bounded by
  `max_message_length`).
- NFKC expansion/contraction forces character-level (rather than
  interval-level) mapping.
- The normalization pipeline order becomes a fixed contract; reordering
  requires a new ADR.

Reversibility: medium. The `SourceMap` shape is internal; raw `SourceSpan`s
and the `CanonicalParserIR` surface are unchanged if the map is re-shaped
later.
