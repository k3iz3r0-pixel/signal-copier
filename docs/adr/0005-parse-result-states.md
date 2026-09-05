# ADR 0005 — Parse Result States

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §14

## Context

The parser must communicate the result of parsing a message
to downstream layers. A continuous "confidence score" is
forbidden by `AGENTS.md` §7 (financial system safety: "Never
make a financial assumption merely because it appears
likely"). A boolean success/failure is too coarse.

The downstream layers need to know:

- Whether to emit a `Signal` or `SignalInstruction`.
- Whether to wait for more messages (multi-message construction).
- Whether to surface the message to a human operator.
- Whether to log the message as a parse failure.

## Decision

The parser emits exactly one of **six discrete states**:

| State | Meaning |
|-------|---------|
| `PARSED` | All required canonical fields present; no conflicts; no ambiguities. |
| `PARTIAL` | Some fields present; some absent WITHOUT being a grammar violation (multi-message construction, percent-dependent SL/TP, direction-only fragment awaiting entry). |
| `AMBIGUOUS` | Multiple valid interpretations. |
| `MALFORMED` | Syntax violates the provider's grammar or is structurally invalid (broken range/number, overflow, oversized input, a `required` rule whose extraction target is absent). A missing numeric entry is NOT, by itself, MALFORMED. |
| `UNSUPPORTED` | Feature not supported by the parser. |
| `NO_SIGNAL` | Not a signal. |

A missing numeric entry must be resolved per the Phase 2 decision
procedure (§14.2): explicit MARKET → PARSED; direction + number without
a trigger → PARSED with `EntryTrigger.UNSPECIFIED` (never promoted to
MARKET); direction-only fragment → PARTIAL; a `required` rule with a
missing extraction target → MALFORMED (per profile); structural breakage
→ MALFORMED.

These six states are a **closed set**. Adding a seventh
requires an explicit ADR and a backward-compatibility
strategy.

The parser returns `ParseResult` = `outcome` (`ParseResultState`)
+ `CanonicalParserIR`. The IR carries `Conflict` and `Ambiguity`
tuples and `MatchEvidence` (rule IDs + spans) so that
downstream layers can make informed decisions without
probabilistic confidence.

## Consequences

Positive:

- The result is auditable; the state is the contract.
- No silent "70% confidence" guesses; the parser either
  knows or says it doesn't.
- The state space is small and testable; every state has
  a defined meaning.
- Downstream layers (OUTPUT ADAPTER, correlation, execution)
  can dispatch on state without ambiguity.

Negative:

- A genuinely uncertain parse produces `AMBIGUOUS`, which
  requires human or correlation intervention. This is the
  correct trade-off in a financial system, but it does
  require operators to handle ambiguity.

Reversibility: low. The state set is part of the parser's
external contract. Changing it is a breaking change.
