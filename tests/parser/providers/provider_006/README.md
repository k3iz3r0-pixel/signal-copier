# Provider 006 — Pending-order style (§21.8).

## Structural family

Explicit "PENDING" prefix + direction/trigger keyword pair + inline
fields ("PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100"). The
pending nature is carried canonically by the ENTRY_TRIGGER fragment
(LIMIT/STOP/MARKET); the "PENDING" word itself is unclaimed decoration.
The pending lifecycle rides the common follow-up actions (CANCEL
PENDING → CANCEL, TRIGGER PENDING → MODIFY+trigger_pending flag).

## Examples

- `PENDING BUY LIMIT EURUSD 1.1000 SL 1.0950 TP 1.1100` → PARSED (LIMIT)
- `PENDING SELL STOP EURUSD 1.2500 SL 1.2550 TP 1.2400` → PARSED (STOP)
- `PENDING BUY LIMIT MARKET EURUSD 1.1000 ...` → AMBIGUOUS (two trigger
  kinds — never silently picked)
- `PENDING BUY SELL EURUSD ...` → MALFORMED (conflicting directions)
- `PENDING BUY LIMIT EURUSD @ 1.1000` → PARTIAL (the "@" breaks the
  number's core adjacency; the number is never guessed)

## Capabilities

Standard set with cancel_pending/trigger_pending/move_sl_number enabled;
profit_close / move_sl_conditional / trailing / multi_signal off.

## Profile fields

```python
provider_name = "provider_006"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits common rules (triggers, SL/TP, actions, conditions). Own rules:
direction LITERAL BUY/SELL, instrument SYMBOL, entry zone BEFORE_TOKEN SL
(occurrence=ALL) + whole-message first-number fallback gated by direction
keyword and symbol (Constraint REQUIRES).
