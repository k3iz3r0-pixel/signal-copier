# Provider 017 — prose `at` entries, NOW wording, `Move SL at` follow-ups.

## Corpus evidence

docs/corpus/real-messages.md M16, M27, M30 (lines 195-198, 309-327,
344-348), quoted VERBATIM in
`tests/fixtures/providers/provider_017/canonical.py`.

## Engine mapping (no pipeline changes)

- Entry: number directly after `at`, gated on BUY/SELL presence;
  common AT_PRICE condition excluded (here `at` IS the entry label).
- NOW → MARKET via a REGEX rule (`\b(NOW)\b`) with FORBIDS [LIMIT]:
  - M30 `SELL NOW at` → MARKET (market execution);
  - M27 `SELL LIMIT now at` → LIMIT only — the adverb `now` must NOT
    become a MARKET trigger. A LITERAL NOW rule cannot express this:
    its keyword-token candidate bypasses constraints and leaves an
    un-gated MARKET next to LIMIT (engine probe → AMBIGUOUS_TRIGGER);
    REGEX sites are constraint-checked.
- `Move SL at <num>` → ACTION_MOVE_SL (level in the evidence snippet);
  M16's `TP1 HIT` status line never binds (ordinal regex requires a
  number after the label; `100+`/`4420` stay unbound PRICE).
- TP: `TP1:/TP2:` ordinal + `TP:` labeled regex rules;
  common.tp.number excluded (the `TP1` ordinal digit must not become a
  phantom TP). SL: inherited common zone rule — safe here because the
  pip annotations keep their sign (`-22 pips`), which stops the zone.

## Covered tests

MARKET now (M30) · LIMIT+adverb guard, no ambiguity (M27) · MOVE_SL
action + status-line immunity (M16) · annotation immunity · prose
NO_SIGNAL / direction-prose PARTIAL · spans · determinism · isolation.
