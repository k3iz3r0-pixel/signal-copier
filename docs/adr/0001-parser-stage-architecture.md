# ADR 0001 — Parser Stage Architecture

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §4-§5

## Context

The parser must convert raw provider messages into canonical
`Signal` / `SignalInstruction` objects (or explicit non-signal
results) without depending on Telegram, Discord, brokers, or
any ingestion layer. It must remain deterministic, testable
in isolation, and manageable for 20+ providers.

A monolithic `if-elif` parser would not scale; a single regex
pass would not preserve enough evidence; a fully agent-based
AI system is forbidden by `AGENTS.md` §26 and the Phase 1
contract.

## Decision

The parser is decomposed into a deterministic compiler-like
pipeline with separated stages:

1. Message Normalization (`RawMessage` → `NormalizedMessage`;
   preserve raw + normalization decisions)
2. Lexical Analysis (`NormalizedMessage` → `tuple[Token, ...]`
   with `SourceSpan`s)
3. Candidate Extraction (`tokens + ProviderProfile` →
   `CandidateGraph`)
4. Rule/Grammar Evaluation (`CandidateGraph + ProviderProfile` →
   `tuple[RuleMatch, ...]`)
5. Semantic Resolution (`tuple[RuleMatch, ...]` →
   `tuple[ParsedFragment, ...]`)
6. Conflict/Ambiguity Analysis (`tuple[ParsedFragment, ...]` →
   `tuple[Conflict, ...]` + `tuple[Ambiguity, ...]`)
7. Canonical Parser IR (fragments + conflicts + ambiguities +
   evidence → `CanonicalParserIR`)

A separate OUTPUT ADAPTER converts `CanonicalParserIR` into
`Signal` / `SignalInstruction` / `NO_SIGNAL` outputs. A
CONTEXT/CORRELATION boundary separates the parser from the
Phase 3+ correlation layer (`CorrelationRequest` contract).

Each stage is a **pure function** with no global state, no I/O,
no time, no randomness. State passes through immutable tuples
and frozen dataclasses.

## Consequences

Positive:

- Each stage is independently testable.
- Source spans and evidence are preserved end-to-end.
- Stage boundaries prevent "monster regex" files.
- A new provider is a new Profile data file, not a parser
  code change.

Negative:

- The pipeline has measurable overhead vs a single regex
  pass. (Phase 3+ implementation will benchmark.)
- Multi-stage debugging requires stage-level evidence.
- Profile composition must be carefully designed to avoid
  stage-level incompatibilities.

Reversibility: high. The pipeline can be folded into a single
function for benchmarks; the canonical IR and OUTPUT ADAPTER
remain stable.
