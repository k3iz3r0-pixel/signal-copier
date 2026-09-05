# Provider 013 — bracket-annotated ticket blocks (REAL corpus family).

## Corpus evidence

docs/corpus/real-messages.md M1-M4 (lines 1-48), quoted VERBATIM in
`tests/fixtures/providers/provider_013/canonical.py`. M3 carries the
family's channel link; M1/M2/M4 share the same ticket/decoration grammar.
Classification: M2 NEW_SIGNAL · M1 EVENT · M3 REPORT · M4 ACTION.

## Engine mapping (no pipeline changes)

- `NEW`-header gating: direction/entry are REGEX rules with
  `REQUIRES [NEW]` — closed events (M1) and weekly reports (M3) carry no
  NEW marker and stay NO_SIGNAL. LITERAL rules cannot be used for the
  gated fields: their keyword-token candidates bypass constraints.
- Field rules are REGEX (`Entry:` / `SL:` / `TP:`): `normalize` strips
  markdown brackets, so zone rules would absorb the pips annotations
  (`[39.9 Pips]`) as phantom values → conflicts. Regex sites match
  exactly; annotations stay unbound PRICE candidates (evidence).
- `Old SL:` is FORBIDS-gated on the SL rule (M4 action block: old/new SL
  must never double-bind).
- `New SL: x` → ACTION_MOVE_SL (level in the evidence snippet);
  `Stop moved to Breakeven` is the prose duplicate of the same move —
  the numeric new-SL is the operative instruction (no BREAKEVEN rule:
  two actions would conflict).
- `Stop` tokens are SL stopwords here, not stop orders —
  common.trigger.stop excluded.

## Covered tests

M2 full fields + annotation immunity · M1/M3 NO_SIGNAL · M4 action with
old-SL immunity · un-gated prose NO_SIGNAL · spans · determinism ·
isolation.
