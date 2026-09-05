# ADR 0002 — Rule Decomposition Strategy

- Status: Accepted (Phase 2 design)
- Date: 2026-08-31
- Phase: 2 (Parser Engine — DESIGN)
- Deciders: Architect
- Source of truth: `docs/phase-2-parser-engine-design.md` §7, §12, §14

## Context

20+ signal providers with substantially different syntax
require a parsing strategy that does not become 20+ monolithic
Python parsers. Regex-only would be unmaintainable for 20+
providers with overlapping rules. Pure Python would be too
verbose. AI-based rule inference is forbidden by `AGENTS.md`
§26 and the Phase 1 contract.

The provider-syntax → canonical-semantics gap is real and
must be bridged by something testable, auditable, and
versioned.

## Decision

Rules are **declarative data** organized in a `RuleSet`.
Each rule is a `ProviderRule` frozen dataclass with:

- `id` (stable string, e.g., `"provider_alpha.entry.buy_limit"`)
- `category` (ENTRY, SL, TP, ACTION_*, ...)
- `matcher` (`MatcherSpec`: literal / regex / token_sequence /
  symbol / alias / number / price / price_range)
- `scope` (`ScopeSpec`: whole_message / line / section /
  after_token / before_token / between_anchors / reply /
  quoted_message)
- `constraints` (`Constraint`: requires / forbids / required /
  requires_reply / requires_context / mutually_exclusive /
  repeatable / uniqueness)
- `target` (SemanticTarget: direction / instrument / entry /
  entry_geometry / entry_trigger / SL / TP / action / condition /
  metadata)
- `priority` (lower = higher priority)
- `occurrence` (FIRST / LAST / NTH / ALL)

A `RuleSet` holds ordered `ProviderRule`s plus `parent`
(single-parent inheritance), `overrides` (renamed masking
`(rule_id, inherited_rule_id)`), and `exclusions`. Rules are NOT
encoded as giant regex; regex is one matcher kind among many.

Rule inheritance is SINGLE-parent and deterministic (§12.5):
the chain is linearized leaf→root; multiple inheritance is
PROHIBITED. A derived `RuleSet` overrides a base rule by
re-declaring the same `rule_id`; `exclusions` remove inherited
ids; `overrides` mask an inherited id with a differently-named
derived rule. Duplicate rule ids within one `RuleSet`, missing
parents, inheritance cycles, conflicting overrides, and
unsupported profile versions are deterministic profile load
errors. Exactly one effective `RuleSet` is computed per
`ProviderProfile` at load time.

Profiles are stored as TOML / Python dict data files under
`packages/parser_profiles/data/<provider>.toml`. Adding a new
provider is adding a Profile data file, not modifying parser
Python code. (Adding a new RULE CATEGORY requires parser code
change and a new ADR.)

## Consequences

Positive:

- Provider-specific syntax is isolated in a single data file.
- Common syntax is shared via RuleSet inheritance.
- Rule changes are auditable as data diffs.
- Tests are per-provider, in `tests/parser/providers/<name>/`.
- New providers can be added without touching parser core.

Negative:

- Profile data is a new artifact to validate (Phase 3+ must
  include a Profile schema + static rule validator).
- A poorly-written Profile can produce ambiguous matches
  (mitigated by inheritance + strict validators).
- Hot-reload of Profiles is not in scope for Phase 2.

Reversibility: medium. Changing the rule model to e.g. Python
classes would be a large refactor; the IR and OUTPUT ADAPTER
are unaffected.
