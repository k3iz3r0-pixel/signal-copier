# Provider 014 — core real-world one-liners and labeled levels (REAL corpus family).

## Corpus evidence

docs/corpus/real-messages.md M5, M6, M9-M13, M17, M21, M22, M24, M25, M31
— the corpus's dominant family (inline core signals, one-liners and
labeled blocks), quoted VERBATIM in
`tests/fixtures/providers/provider_014/canonical.py`. This profile
validates the COMMON grammar against real data and adds the
corpus-required variants.

## Engine mapping (no pipeline changes)

- Entry set: after-direction zones (BUY/SELL), `Entry` label, after
  `limit`, after `now`, symbol-adjacent whole-message rule (binds ONLY
  symbol-adjacent numbers — prose numbers like M9's `300/250` can never
  be hijacked), PRICE_RANGE gated on a co-occurring SL token.
- Slash ranges → PriceRange + RANGE geometry (§7.3 longer-match; both
  endpoints preserved; the pair is claimed by the range rule).
- SL/TP: REGEX labeled rules (`\bSL\s*:?\s*(num)` — case-insensitive,
  handles `SL:`, plain `SL`, lowercase `sl`) — annotation numbers
  (`(-25pips)`, `(18.2 pips)`) are outside the regex match and never
  bound. Repeated unlabeled TPs merge in message order (ALL).
- `Stop loss:` SL via AFTER_TOKEN LOSS + TAKE-gated `Take profit:` TPs;
  common.trigger.stop excluded (`Stop` here is a stopword, NOT a stop
  order — M22 would otherwise get a bogus STOP trigger).
- `now` → MARKET canonical (FORBIDS LIMIT) — M24 market sell with the
  entry preserved; geometry MARKET.
- No-entry messages (M22, M25) → PARTIAL with entry_pending; M21 (no TP)
  → PARSED with TP optional; commentary (M6) → NO_SIGNAL.

## Covered tests

Ranges (M12/M13) · repeated-TP order (M11) · labeled prose levels (M9,
M22) · lowercase one-liner (M21) · MARKET now (M24) · PARTIALs (M22/M25)
· symbol-adjacent + annotations (M31) · commentary (M6) · conflicting
directions → MALFORMED · spans · determinism · isolation.
