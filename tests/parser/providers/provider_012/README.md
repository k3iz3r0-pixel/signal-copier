# Provider 012 — Follow-up SL/TP modification actions (INFERENCE).

## Structural family

Update-style messages that move SL/TP levels of a previous signal:

- `MOVE SL TO 1.0900` (standalone)
- `EURUSD MOVE SL 1.0900`
- `MOVE TP TO 1.1300`
- `MOVE SL TO BE` (breakeven)

No §21 example is a dedicated follow-up family; the SEMANTICS are fully
documented (§20.9, §20.13, §20.14) — only the `MOVE SL|TP TO <number>`
phrasings are new, and they are synthetic (INFERENCE).

## Engine mapping (no pipeline changes)

- Own REGEX rules `p012.action.move_sl_to` / `p012.action.move_tp_to`
  capture the new level (group 1) as ACTION fragments.
- Everything else is inherited common behavior:
  - standalone `MOVE SL TO x` (no instrument) → `follow_up_only`
    NO_SIGNAL + CorrelationRequest TARGET_LAST_SIGNAL (§20.13);
  - `EURUSD MOVE SL x` / `EURUSD SL x` → PARSED MOVE_SL action (§20.13);
  - `CHANGE TP TO x`, `CHANGE ENTRY TO x`, `REMOVE SL`, `CLOSE ...`,
    `MOVE SL TO BE` → inherited common action rules.
- Action-context suppression: an update message must not look like a
  new signal — the TP number in `MOVE SL TO 1.2500 TP 1.2600` is
  preserved as a candidate but not fragment-bound (its binding rule
  declares no direction keywords).
- False positive: `(was 1.0850)` parentheticals never bind (the common
  move_sl regex requires `SL <number>` adjacency; "was" breaks it).

## Examples

- `MOVE SL TO 1.0900` → NO_SIGNAL + ACTION MOVE_SL + follow_up_only
- `EURUSD MOVE SL 1.0900` → PARSED (ACTION MOVE_SL)
- `MOVE TP TO 1.1300` → PARSED (ACTION MOVE_TP)
- `MOVE SL TO BE` → PARSED (BREAKEVEN, §20.9)
- `MOVE SL TO 1.0900 MOVE TP TO 1.1300` → MALFORMED (ACTION conflict,
  both values preserved)
- `MOVE SL TO 1.0900 (was 1.0850)` → `1.0850` stays an unbound PRICE

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_012"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits ALL common rules unchanged. Own rules: the two MOVE SL|TP TO
REGEX actions. No direction/instrument/entry rules — this family never
opens signals.
