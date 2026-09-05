# Provider 011 — Lot/quantity-bearing inline signals (INFERENCE).

## Structural family

Inline signals that carry a lot-size quantity BEFORE the prices:

`BUY EURUSD 0.5 LOTS @ 1.1000 SL 1.0950 TP 1.1100`

No §21 example carries a quantity; it is a synthetic member of the
false-positive-numeric axis (§21 examples are themselves marked
INFERENCE).

## Engine mapping (no pipeline changes)

- Entry = LAST number in the BEFORE_TOKEN SL zone (`occurrence=LAST`).
  The canonical zone is `BUY EURUSD 0.5 LOTS @ 1.1000`; its last number
  is the real entry. A naive core-adjacency rule would mis-bind `0.5`
  (it sits directly after the symbol) — the LAST-in-zone rule is the
  provider-declared, deterministic alternative.
- `@` is not glue, so the zone stops there; the zone scan is what makes
  the `@`-form work without any adjacency special case.
- NO whole-message entry rule: no other number can silently become the
  entry.
- The frozen Phase 2A contract has NO quantity field — the lot size is
  never bound; it stays an unbound PRICE candidate (§16.4: unsupported
  semantics are never invented). Documented as a contract boundary, not
  a defect.

## Examples

- fractional lots → PARSED (ENTRY=1.1000; `0.5` unbound)
- integer lots → PARSED (`2` unbound)
- two entry numbers in the zone → MALFORMED + ENTRY conflict (preserved)
- no-lots `@` form → PARSED
- lots-only message `BUY EURUSD 0.5 LOTS` → PARTIAL (entry_pending; `0.5`
  unbound — quantity alone is not an entry)

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_011"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits ALL common rules unchanged. Own rules: direction LITERAL
BUY/SELL, instrument SYMBOL, entry NUMBER BEFORE_TOKEN SL with
occurrence LAST (direction-keyword gated).
