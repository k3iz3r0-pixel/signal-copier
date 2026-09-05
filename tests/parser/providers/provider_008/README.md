# Provider 008 — Colon key-value field tables (INFERENCE).

## Structural family

Fields as `Label: value` pairs joined by `|` separators, either on one
line or one pair per line:

`Pair: EURUSD | Side: BUY | Entry: 1.1000 | SL: 1.0950 | TP: 1.1100`

No §21 example uses this exact syntax; it is a synthetic member of the
line-structured axis (§21 examples are themselves marked INFERENCE).
No new semantics.

## Engine mapping (no pipeline changes)

- `:` and `|` are DECLARED `field_separators`, which makes them glue
  (§7.4): the value zone after `SL` spans `SL: 1.0950` exactly like
  `SL 1.0950`, and the zone stops at the first non-value token
  (`Ref:` prose) so trailing reference numbers never bind.
- Entry = the number between the `Entry:` label and the `SL` label
  (BETWEEN_ANCHORS).
- SL/TP override the common rules with renamed variants that declare
  direction keywords, so a signal-plus-action message keeps its signal
  fragments (action-context tolerance, `_fragments_from_winners`).

## Examples

- canonical pipe table → PARSED (all slots)
- one pair per line → PARSED
- two `Entry:` values → MALFORMED + ENTRY conflict (both preserved)
- missing `Entry:` → PARTIAL + entry_pending
- trailing `Ref: 90210` → reference number stays an unbound PRICE candidate

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_008"
version = "2B"
field_separators = [":", "|"]
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits common rules EXCEPT common.sl.number and common.tp.number
(renamed overrides `p008.sl.colon`, `p008.tp.colon`). Own rules:
direction LITERAL BUY/SELL, instrument SYMBOL, and the
BETWEEN_ANCHORS entry rule.
