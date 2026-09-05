# Provider 015 — labeled scalp cards with past-tense entries (REAL corpus family).

## Corpus evidence

docs/corpus/real-messages.md M7, M8 (lines 71-117), quoted VERBATIM in
`tests/fixtures/providers/provider_015/canonical.py`. The family
self-identifies in-corpus (FXG prefix + site URL in the same messages).

## Engine mapping (no pipeline changes)

- Direction: Long/Short/BOUGHT/SOLD LITERAL canonicals (same-value
  duplicates — Long AND BOUGHT in one card — dedupe to one fragment).
- Entry: number directly after `at`, gated on BOUGHT/SOLD presence;
  common AT_PRICE condition excluded (here `at` IS the entry label).
- SL/TP: REGEX rules — the bracket annotations (`[1 Pips]`, `[1R]`)
  lose their brackets in normalization; zone rules would absorb them as
  phantom conflicts. Regex sites match exactly; TP1/TP2/TP3 merge in
  message order.
- Noise immunity: `±78%`, `Position Size: 2%`, `$1K … 100 Lots`,
  `21.28 Lots`, ticket numbers — never bound (no rule zone reaches
  them; whole-message numeric rules bind only symbol-adjacent numbers).

## Covered tests

Canonical cards (M7/M8) · direction dedupe · noise/R-multiple immunity ·
prose NO_SIGNAL · spans · determinism · isolation.
