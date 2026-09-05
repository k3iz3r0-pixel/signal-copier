# Provider 009 — Prose sentences with synonym keywords (INFERENCE).

## Structural family

Sentence-style messages: direction as `Long`/`Short`, SL as `Stop`,
TP as `Target`, arbitrary prose around the fields, any casing:

`We go long EURUSD 1.1000 stop 1.0950 target 1.1100 now`

No §21 example uses this exact syntax; it is a synthetic member of the
prose-heavy axis (§21 examples are themselves marked INFERENCE).

## Engine mapping (no pipeline changes)

- `Long`/`Short` → canonical `BUY`/`SELL` via the rule-level `canonical`
  param (§21.3 pattern); raw text preserved in `canonical_alias` evidence.
- Keyword classification is case-insensitive (§5.4), so prose casing
  parses identically (`stop` == `Stop` == `STOP`).
- `Stop`/`Target` synonyms: common SL/TP rules are EXCLUDED and replaced
  by four explicit AFTER_TOKEN rules (`p009.sl.number`, `p009.sl.stopword`,
  `p009.tp.number`, `p009.tp.targetword`) — AFTER_TOKEN scopes use the
  FIRST anchor only, so each synonym needs its own rule.
- `Stop` must NOT become a pending STOP trigger → `common.trigger.stop`
  is EXCLUDED (this family never sends pending orders).
- Prose `at <price>` is an entry preposition, not a conditioned action →
  `common.condition.at_price` is EXCLUDED; the word `at` breaks §5.6 core
  adjacency, so the entry stays UNRESOLVED (PARTIAL) instead of guessed.
- SL/TP rules declare direction keywords, so a signal-plus-action message
  keeps its signal fragments (action-context tolerance).

## Examples

- `Long EURUSD 1.1000. Stop 1.0950. Target 1.1100.` → PARSED
- lowercase prose variant → PARSED (identical semantics)
- `Long ... Short EURUSD 1.1500.` → MALFORMED (DIRECTION + ENTRY conflicts preserved)
- `Long EURUSD at 1.1000 ...` → PARTIAL (entry unresolved, value preserved)
- `stop loss and target talk, no trade` → NO_SIGNAL (no direction keyword)

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_009"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = False
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"]]
```

## Rules

Inherits common rules EXCEPT common.sl.number, common.tp.number,
common.trigger.stop, common.condition.at_price (exclusions). Own rules:
Long/Short canonical directions, instrument, whole-message entry
(direction-keyword gated), and the four synonym SL/TP rules.
