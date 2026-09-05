# ADR 0011 — Provider Capabilities vs Rules (Extensibility)

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §12, §19

## Context

20+ providers differ in what they can express (capabilities)
and in how their syntax maps to canonical semantics (rules).
If capabilities are entangled with parsing rules, adding a
provider with a known capability in a different syntax would
require touching both the engine and the profile, and
validation of "can this provider even express X" becomes
impossible.

## Decision

`ProviderCapabilities` (what a provider CAN express) is
declared separately from `ProviderRule`s (how it is parsed).
Capabilities are validated at profile load time; rules are
interpreted at parse time.

`ProviderCapabilities` remains CAPABILITY-ORIENTED: it declares
only WHAT a provider can express (booleans). It MUST NOT grow
into a mirror of provider syntax. Syntax and lexical specifics
(keyword vocabulary, separators, decimal/range formats, matcher
patterns) belong in the `ProviderProfile` syntax fields and in
`ProviderRule`s, never as capability flags. A capability flag
exists only when (a) it is meaningfully "can express X", and
(b) downstream logic or validation needs to branch on it
independent of syntax. If a flag would duplicate rule/grammar
data, it is a rule, not a capability.

Provider architecture is a composition chain:

```text
Common rules
  → domain-specific shared rules (forex / crypto / index)
    → provider profile
      → provider overrides
        → provider exclusions
```

Adding provider #21 requires only a `ProviderProfile` +
`RuleSet` + fixtures; generic parser logic is NOT modified
unless the provider exposes a genuinely new capability. A new
capability is added as a new `ProviderCapabilities` flag +
new `ProviderRule` category, with an ADR; the generic engine
is extended ONCE, not per-provider.

This is codified as an architectural acceptance test: adding
a new provider with only a profile + rules + fixtures must
not require modifying the generic parser engine. If engine
modification is required, the design must identify why.

## Consequences

Positive:

- Extensibility is verifiable by test.
- Capability discovery is independent of syntax.
- Provider additions stay data-only in steady state.
- Genuinely new capabilities get a documented, one-time engine
  extension path.

Negative:

- Two artifacts (capabilities + rules) must be kept consistent
  (Profile validator checks this).
- A "new capability" is a heavier change than a new provider.

Reversibility: medium. Splitting capabilities from rules is a
Profile schema decision; the IR surface is unaffected.
