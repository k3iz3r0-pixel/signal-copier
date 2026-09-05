# Provider 010 — Unusual field ordering (INFERENCE).

## Structural family

SL/TP fields placed BEFORE the entry, or the TP first, or the instrument
AFTER all price fields:

- `BUY SL 1.0950 TP 1.1100 EURUSD 1.1000`
- `TP 1.2400 SELL EURUSD 1.2500 SL 1.2550`
- `BUY 1.1000 SL 1.0950 TP 1.1100 EURUSD` (symbol last)

No §21 example uses this ordering; it is a synthetic member of the
unusual-field-ordering axis (§21 examples are themselves marked
INFERENCE). No new semantics.

## Engine mapping (no pipeline changes)

- Whole-message entry rule (direction keywords + symbol presence, §5.6
  REQUIRES) binds the number that is CORE-ADJACENT to a symbol token —
  independent of where the SL/TP anchors sit.
- Common SL/TP AFTER_TOKEN zones are BOUNDED (glue + numbers only, §7.4):
  `SL 1.0950 TP ...` stops the SL zone at the `TP` keyword, so the TP
  number is never stolen and ordering cannot cross-contaminate fields.
- Symbol-last form: the number preceding `BUY` is not core-adjacent to
  the symbol (which trails the message), so the entry stays UNRESOLVED →
  PARTIAL + entry_pending; the value is preserved as an unbound PRICE
  candidate (§5.6 — no guessing).

## Examples

- `BUY SL 1.0950 TP 1.1100 EURUSD 1.1000` → PARSED
- `TP 1.2400 SELL EURUSD 1.2500 SL 1.2550` → PARSED
- `BUY 1.1000 SL 1.0950 TP 1.1100 EURUSD` → PARTIAL (entry_pending)
- `BUY SL 1.0950 EURUSD 1.1000` (no TP) → PARSED
- `SELL ... BUY` mixed directions → MALFORMED (DIRECTION conflict preserved)

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_010"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits ALL common rules unchanged. Own rules: direction LITERAL
BUY/SELL, instrument SYMBOL, whole-message entry rule. This profile is
deliberately minimal — it exercises the engine's order-independence
rather than adding syntax.
