# Provider 007 — Ordinal take-profit labels (INFERENCE).

## Structural family

Inline signal with ordinal-labeled take-profits instead of the slash
multi-value form: `BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950`.
No §21 example uses this exact syntax; it is a synthetic member of the
"multiple TP forms" axis (§21 examples are themselves marked INFERENCE).
No new semantics: ordinal labels denote TP levels exactly like the
documented slash form.

## Engine mapping (no pipeline changes)

- "TP1" tokenizes as TP + ordinal NUMBER; the inherited common TP rule
  would mis-bind the ordinals, so the profile EXCLUDES
  `common.tp.number` and adds REGEX `TP\d\s+(number)` (group 1 = level,
  occurrence=ALL).
- Entry = the number between the direction keyword and the first TP
  label, via BETWEEN_ANCHORS NUMBER rules (one per direction). Ordinal
  digits cannot pollute it (they live after the TP anchor).

## Examples

- `BUY EURUSD 1.1000 TP1 1.1100 TP2 1.1200 SL 1.0950` → PARSED
  (TP = 1.1100, 1.1200; ordinals preserved as unbound PRICE candidates)
- `SELL EURUSD 1.2500 TP1 1.2400 TP2 1.2300 TP3 1.2200 SL 1.2550` → PARSED
- reordered `... SL 1.0950 TP1 ... TP2 ...` → PARSED (SL zone claim wins)
- two numbers before the first TP label → MALFORMED (ENTRY conflict preserved)

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_007"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits common rules EXCEPT common.tp.number (excluded). Own rules:
direction LITERAL BUY/SELL, instrument SYMBOL, two BETWEEN_ANCHORS entry
rules, and the labeled-TP REGEX rule.
