# ADR 0004 — Canonical IR Surface

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §13

## Context

The parser produces canonical semantics, not Signal Core
instances. The boundary between "parser output" and "Signal
Core input" must be a well-defined value surface that:

- Contains no provider-specific tokens, regex patterns, or
  symbol aliases.
- Is convertible 1:1 into `Signal` / `SignalInstruction` /
  `NO_SIGNAL` (or other explicit non-signal result).
- Carries enough evidence to make the parse result auditable.
- Is deeply immutable and conformant to
  `ALLOWED_SNAPSHOT_TYPES` when serialized.

A `CanonicalParserIR` that contains provider-specific data
would defeat the purpose of the IR.

## Decision

The IR is `CanonicalParserIR`, a frozen dataclass preserving:

- `candidates` (post-resolution `Candidate` tuples);
- `unresolved_fields` (slots present but unresolved);
- `fragments` (`ParsedFragment` tuples);
- `conflicts` (`Conflict` tuples);
- `ambiguities` (`Ambiguity` tuples);
- `evidence` (`MatchEvidence` tuples);
- `normalization_decisions`;
- `context_reference` (`ContextReference | None`);
- `correlation_request` (`CorrelationRequest | None`);
- `conditions` (`Condition` tuples);
- `provider_id`;
- `source_ref` (for re-parse / replay);
- `parser_version`.

The parser returns `ParseResult`, a wrapper of `outcome`
(`ParseResultState`, 6-state closed set) plus the
`CanonicalParserIR`.

The parse outcome has exactly ONE authoritative owner:
`ParseResult.outcome`. `CanonicalParserIR` carries NO `outcome` field.
The invariant is `ParseResult.outcome == derive_outcome(ParseResult.ir)`,
where `derive_outcome` is a single pure function of the IR contents
(unresolved fields, conflicts, ambiguities) together with the parser's
§14 stage-level decisions (grammar violations, media-only / empty /
deleted messages, unsupported features), which are not IR fields; it is
implemented in Phase 3+. The Phase 2A contract layer enforces only the
structural part: one owner, and no `outcome` field on the IR. The
outcome is DERIVED, never stored in it, and never computed by a second
independent code path.

Fragments and candidates use ONLY canonical types from
`packages/signal_core` (no provider-specific enums, no
provider-specific text). `MatchEvidence` records carry
`span: SourceSpan | None` pointing into the raw text and
`rule_id: str | None`. The raw text itself is NOT duplicated
in the IR; it is referenced by span and retrievable from the
source.

The IR conforms to `ALLOWED_SNAPSHOT_TYPES` for the parts
that are eventually serialized into a `canonical_snapshot`
(per `docs/canonical-snapshot-contract.md`).

The OUTPUT ADAPTER (a separate module) is the ONLY component
that converts `CanonicalParserIR` into `Signal` or
`SignalInstruction` instances. Signal Core receives only
resolved canonical semantics.

## Consequences

Positive:

- Parser and Signal Core are decoupled; Signal Core never
  observes provider syntax.
- The IR is the contract; changing the IR shape requires an
  ADR but not a parser code rewrite.
- Evidence is preserved end-to-end; the parse result is
  auditable.
- The IR is a frozen value, safe to pass across threads and
  to serialize.

Negative:

- The IR has many fields; future extensions must be careful
  about backward compatibility.
- The OUTPUT ADAPTER is a new module to implement and test.

Reversibility: medium. Adding a field to the IR is easy;
removing one requires migration of fixtures.
