# ADR 0008 — Candidate Graph (Competing Candidates)

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §5-§6

## Context

A provider message can contain multiple competing
interpretations for the same semantic slot. Example:

```text
direction:
  candidate A = BUY
  candidate B = SELL
```

If the parser immediately collapses extracted information
into a dict, the competing candidates are lost and the
resolver can no longer explain why it chose one value (or
declare ambiguity). In a financial system, silently dropping
a competing SELL candidate when a BUY candidate exists is
unsafe.

## Decision

Extracted information is represented as a `CandidateGraph`,
a frozen dataclass that preserves multiple `Candidate`
values per `CandidateSlot` until resolution. Each
`Candidate` carries its canonical value, `SourceSpan`, and
provenance (`MatchEvidence`).

The resolver classifies relationships between competing
candidates into exactly four outcomes:

| Relationship | Meaning | Action |
|--------------|---------|--------|
| `compatible` | Different slots, or same value from independent evidence. | Keep both; merge evidence. |
| `duplicate` | Same slot, same value, same span, different rule IDs. | Collapse with merged evidence. |
| `conflicting` | Same slot, different values (contradiction). | Emit `Conflict`. |
| `ambiguous` | Same slot, multiple valid values, no contradiction. | Emit `Ambiguity`. |

Rule override is NOT a candidate relationship. It is resolved at
rule-evaluation time (§12.5): a provider rule replaces an inherited rule
BEFORE candidates are extracted, so only one candidate results. The
override is recorded as `MatchEvidence` with `kind = "provider_override"`
(provenance), not as a fifth resolver outcome. If a provider rule and an
inherited rule both produce candidates for the same slot anyway, they are
classified `duplicate` or `conflicting` like any other candidates.

## Consequences

Positive:

- Competing interpretations are preserved for audit.
- The resolver can always explain its choice with evidence.
- Ambiguity and conflict are distinct, testable outcomes.
- Provider-specific overrides do not produce false conflicts.

Negative:

- The `CandidateGraph` is larger than a flat dict; memory
  and comparison cost must be benchmarked in Phase 3+.
- Resolution logic is more complex than "first match wins".

Reversibility: medium. The graph shape is internal to the
parser; the `CanonicalParserIR` surface can remain stable if
the graph is simplified later.
