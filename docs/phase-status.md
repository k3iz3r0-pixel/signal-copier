# Phase Status — Authoritative

This document is the SINGLE authoritative source for the project's current
phase status. Per AGENTS.md §2.3 (source-of-truth hierarchy) and §3 (phase
discipline), no other document may claim a different phase status without
explicit approval and a corresponding update to this file.

If a future task contradicts the status below, STOP and report the conflict.
Do not silently reinterpret.

## Current Status

```text
Current Phase:          Phase 2 — Parser Engine
Current Phase Status:   IMPLEMENTATION COMPLETE (adopted scope; reconciled 2026-09-05)
Previous Phase:         Phase 1 — Signal Core (COMPLETE)
Previous Phase:         Phase 1.1 — Architecture Freeze / Remediation (COMPLETE)
Phase 2 Implementation: COMPLETE (adopted Phase 2A–2F scope + output adapter)
Phase 2 Implementation Approval: GRANTED (owner adoption decision, 2026-09-05)
Next Phase:             Phase 3 — NOT STARTED, NOT APPROVED
Release State:          Committed locally; NOT pushed (push requires explicit owner approval)
```

## Phase 1 — Signal Core

Status: **COMPLETE**

Phase 1 delivered the canonical, deterministic, provider-agnostic,
broker-agnostic domain model for trading signals, with no parser, no provider
adapter, no broker adapter, no Telegram/Discord, no database, no Redis, no
execution, no strategy, no risk, no replay, no backtesting, no analytics, no
AI.

Delivered components (all under `packages/signal_core/`):

- Enums: `TradeDirection`, `EntryGeometry`, `EntryTrigger`, `LifecycleState`
  (DRAFT / ACTIVE / CANCELLED / EXPIRED / ARCHIVED only), `SignalStatus`,
  `EventType`, `InstructionType`, `SourceType`, `AssetClass`.
- Value objects (frozen dataclasses): `Price`, `PriceRange`, `ProviderSource`,
  `SourceIdentity`, `Instrument`.
- Domain objects (frozen dataclasses): `SignalIdentity`, `Signal`,
  `SignalRevision`, `SignalEvent`, `SignalInstruction`.
- Pure invariant functions in `invariants.py` (no class-level validators).
- Unified canonical-value validator/normalizer used by `SignalRevision`,
  `SignalEvent.event_payload`, `SignalInstruction.payload`, and
  `canonical_fingerprint` (single contract — see `ALLOWED_SNAPSHOT_TYPES`).

Documentation:

- `docs/phase-1-signal-core-design.md` — design specification.
- `docs/invariant_matrix.md` — invariant coverage matrix.
- `docs/architecture.md` — repository structure.
- `docs/principles.md`, `docs/agent_instructions.md` — engineering principles.

## Phase 1.1 — Architecture Freeze / Remediation

Status: **COMPLETE**

Purpose: Before Phase 2 (parser) begins, freeze the Phase 1 architecture by
auditing, unifying, and documenting all foundational contracts.

Delivered:

- Authoritative phase-status document (this file).
- Documentation consistency (remove stale "Phase 0" claims; document the
  current Phase 1 state).
- Resolution of historical design-document revisions so that no obsolete
  definitions (e.g., `EXECUTING`/`EXECUTED` as lifecycle states) appear as
  equally authoritative.
- Canonical-fingerprint contract audit (duplicate keys; validator/normalizer
  parity with `SignalRevision`). 2 defects found, regression tests added
  (test count: 321 → 334).
- Unification of the validator/normalizer contract across fingerprint,
  revision, event payload, instruction payload.
- Documentation of the `Signal → canonical projection → canonical snapshot
  → SignalRevision` contract (`docs/canonical-snapshot-contract.md`).
- No parser, no provider adapter, no broker adapter, no Telegram, no
  Discord, no database, no Redis, no execution, no strategy, no risk, no
  replay, no backtesting, no analytics, no AI.

## Phase 2 — Parser Engine

Status: **IMPLEMENTATION COMPLETE (adopted scope)**

### Adoption record

On 2026-09-05 the owner explicitly authorized adoption of the existing
Phase 2A–2F implementation as the basis for reconciliation ("I authorize
adoption of the existing Phase 2A–2F implementation as the basis for the
next reconciliation"). This decision retroactively satisfies the four
implementation preconditions that an earlier revision of this file required
(design approval; ADR review; fixture-catalog review; explicit instruction to
begin implementation) and authorizes reconciliation, completion, verification,
and commit of that work. It does NOT authorize new architecture beyond the
authoritative design, Phase 3 work, or the deferred items below.

### Delivered (verified by the current test suite: 940 tests)

- Design artifacts: `docs/phase-2-parser-engine-design.md`;
  ADRs `docs/adr/0001`–`0013` (ADR 0013 = multi-block signal messages,
  Phase 2E, as-built contract recorded in its "Phase 2E audit deviations"
  section).
- Phase 2A contract layer: `packages/parser/types.py`, `enums.py` —
  `RawMessage`, `MessageMetadata`, `NormalizedMessage` + `SourceMap`/`SourceSpan`
  (ADR 0012), `Token`, `Candidate`/`CandidateGraph`, `RuleMatch`, `Conflict`,
  `Ambiguity`, `MatchEvidence`, `ParsedFragment`, `ContextReference`,
  `CorrelationRequest`, `EditDelta`, `CanonicalParserIR`, `ParseResult`,
  `ProviderCapabilities`, `ProviderRule`, `RuleSet`, `ProviderProfile`,
  `MessageBlock`/`BlockParse` (ADR 0013). Structural single-owner invariant:
  `ParseResult.outcome` is the only outcome owner; the IR carries no outcome.
- Phase 2B engine: `packages/parser/pipeline.py` (normalize → tokenize →
  extract candidates → evaluate rules → resolve semantics → `ParseResult`;
  `PARSER_VERSION` in the module), `packages/parser/profiles.py` (profile
  loader + effective-RuleSet resolution), `packages/parser/safety.py` (static
  bounded regex validator, message/numeric/token/candidate bounds, charset
  hardening, profile divider matchability validation).
- Phase 2C providers + real corpus: `packages/parser_profiles/data/`
  (`common.py` + `provider_001`–`provider_017`; 001–012 synthetic, 013–017
  VERBATIM excerpts of the owner-supplied corpus
  `docs/corpus/real-messages.md`, M1–M32); fixture data
  `tests/fixtures/providers/`; per-provider tests
  `tests/parser/providers/provider_001`–`provider_017`; classification and
  evidence model in `docs/corpus/EVIDENCE.md`.
- Phase 2D safety hardening and adversarial suites:
  `tests/parser/adversarial/` (ReDoS, unicode bidi, overflow, price-range
  invariant, action/event separation).
- Phase 2E multi-block (ADR 0013): `ParseResultState.MULTI_SIGNAL`;
  `MessageBlock`/`BlockParse`/`ParseResult.blocks` (None = legacy
  single-unit; ≥2 blocks only); profile-declared `section_dividers` (default
  empty ⇒ providers 001–017 remain on the provably legacy path); mechanical
  block segmentation; block-local candidate/rule/resolution evaluation
  (cross-block capture impossible by construction); duplicate-feed
  `duplicate_of` marking via structured payload fingerprint (comparison
  only; parser never collapses duplicates); deterministic outcome
  aggregation with MALFORMED > UNSUPPORTED > AMBIGUOUS escalation.
- Phase 2F adversarial audit: linear-scaling segmentation (1600-block
  messages), inert-divider rejection at load, 26 multi-block adversarial
  tests (`tests/parser/blocks/`).
- OUTPUT ADAPTER (design §25 step 5): `packages/parser/output_adapter.py` —
  the ONLY converter of `CanonicalParserIR` into `Signal`,
  `SignalInstruction`, or an explicit non-signal result (ADR 0004).
  Caller-supplied `SignalIdentity` (design §4.4: identity UUIDs are produced
  by the integration layer, never the parser); timestamps from
  `MessageMetadata`; caller-supplied symbol → `Instrument` mapping (no
  AssetClass inference — design §23 open question 8); missing trigger →
  `EntryTrigger.UNSPECIFIED` (never promoted to MARKET — design §4.3);
  lossless action payloads (design §8, §10.1 layer E, §20.10–§20.15,
  ADR 0009), including action operands recovered from resolved winners;
  representational conflicts surfaced as stable NON_SIGNAL reasons (see
  below); `MULTI_SIGNAL` aggregates refused (anti-merge rule, ADR 0013 §5).

### Recorded decisions and deferrals (do not treat as complete)

- MULTI_SIGNAL enforcement: declarative only, exactly per ADR 0013 deviation
  #9 — aggregation does not consult the `multi_signal` capability flag, and
  enforcement (e.g. ≥2 executable blocks under `multi_signal=False` ⇒
  UNSUPPORTED) is explicitly a future owner decision. Nothing beyond the
  ADR-authorized semantics was implemented.
- Corpus batch-2 (M14, M15, M18, M29, M28): DEFERRED by owner instruction.
  Implementation requires explicit owner approval.
- REPRESENTATIONAL CONFLICT (recorded, NOT resolved): MARKET entry geometry
  with a preserved entry price (real corpus M24, provider_014) is not
  representable in the Phase 1 `Signal` model, whose invariant requires
  `entry_price is None` under MARKET geometry. The adapter returns
  `NON_SIGNAL("market_geometry_with_entry_not_representable")` and the data
  remains fully preserved in the `ParseResult`. Resolving this requires an
  owner decision (Phase 1 model extension ADR, or Phase 3 correlation-side
  handling). It was deliberately NOT silently resolved by dropping the price
  or re-labeling the geometry.
- Remaining open design questions: design §23 (TRIGGER_PENDING,
  percent-dependent SL/TP, conditional entry, multi-instrument signals,
  hedged pairs, reverse identity policy, exact edit-delta semantics, symbol
  mapping, profile versioning/hot-reload).

Phase 2 is NOT production-ready: no Telegram/Discord ingestion, no broker
adapters, no execution, no strategy, no risk, no database, no Redis, no
replay, no backtesting, no analytics, no AI, no correlation (all Phase 3+ or
later, none approved).

## Maintenance Rule

This document is the only place where "current phase" and "current phase
status" are declared for the project. Other documents may reference the
status but must not redefine it.

A phase transition requires:

1. Explicit user instruction.
2. Updated contents of this file.
3. Updated contents of `docs/architecture.md` and `AGENTS.md` if the
   transition is structural.

No agent may auto-advance the phase.
