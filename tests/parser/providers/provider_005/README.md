# Provider 005 — Multi-line numbered entry levels (§21.7).

## Structural family

"SCALP" header + ordinal-prefixed level lines ("1) 3350") + SL/TP keyword
lines. The LINE-scoped regex captures only the level number (group 1
skips the ordinal), so ordinals themselves can never become prices.
Multiple levels accumulate with order preserved verbatim. The §21.7
example carries no instrument symbol; the parser leaves INSTRUMENT
unresolved and reports PARSED.

## Examples

- `SCALP LONG\n1) 3350\n2) 3340\n3) 3330\nSL 3300\nTP 3400` → PARSED
  (instrument unresolved, ENTRY = 3350/3340/3330 in message order)
- `SCALP LONG EURUSD\n1) 3350\n2) 3340\nSL 3300\nTP 3400\ndated 2026-09-05`
  → PARSED (date chain never becomes a price)
- `SCALP LONG AND SHORT ...` → MALFORMED (conflicting directions preserved)

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_005"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = True
symbol_aliases = [["EURUSD", "EURUSD"], ["XAUUSD", "XAUUSD"]]
```

## Rules

Inherits common rules (SL/TP keywords, actions, conditions). Own rules:
direction LITERAL LONG→BUY / SHORT→SELL / SELL (INFERENCE beyond the
§21.7 example), instrument SYMBOL, and the LINE-scoped numbered-levels
REGEX with occurrence=ALL.
