# Provider 016 — @-separated signal levels (REAL corpus family).

## Corpus evidence

docs/corpus/real-messages.md M23, M26 (lines 282-307), quoted VERBATIM in
`tests/fixtures/providers/provider_016/canonical.py`.

## Engine mapping (no pipeline changes)

- `@` declared as a field separator (glue): `SL @ 67.0731` and
  `TP @ 61.3857` bind through value-zone adjacency.
- Entry: BEFORE_TOKEN SL zone FIRST — the SL value is owned by the SL
  rule, so the entry zone skips it (no double-binding); the `@` between
  instrument and entry does not break the zone.
- TPs: `TP @` regex + `Tp1/Tp2` ordinal regex (ALL, message order);
  common.tp.number excluded — a zone rule would absorb the ordinal
  digit of `Tp1` as a phantom TP value (ordinal digits stay unbound
  PRICE candidates).
- Aliases: XAGUSD (corpus message), GOLD→XAUUSD (corpus-supported
  equivalence).

## Covered tests

@-level binding (M23) · ordinal TPs (M26) · SL/entry non-double-binding ·
ordinal-digit immunity · prose immunity · NO_SIGNAL negative ·
direction-prose PARTIAL (non-executable) · spans · determinism ·
isolation.
