# Provider 001 — Inline, comma-separated fields (Design §21.1).

## Structural family

Single-line, comma-separated field list (commas collapsed to spaces by
normalization). Explicit entry/SL/TP keywords. Decimal-point numbers. Entry
levels are the numbers BEFORE the SL anchor; a price-range form
("2350-2360") outranks a single number by the §7.3 longer-match rule.

## Examples

- `BUY EURUSD 1.1000 SL 1.0950 TP 1.1100` → PARSED (entry=1.1000, SL=1.0950, TP=1.1100)
- `BUY XAUUSD 2350-2360 SL 2340 TP 2400` → PARSED (entry=PriceRange(2350, 2360), geometry=RANGE)
- `BUY LIMIT EURUSD @ 1.1000 SL 1.0950 TP 1.1100` → PARSED (trigger=LIMIT)
- `CLOSE HALF` → PARSED (action=PARTIAL_CLOSE)
- `CLOSE 50%` → PARSED (action=PARTIAL_CLOSE)
- `MOVE SL TO BE` → PARSED (action=BREAKEVEN)
- `BUY` → PARTIAL (direction-only, awaiting entry)
- `BUY EURUSD 1.1000 SL 1.0950 TP 1.1100\nCLOSE` → PARSED (signal + action)

## Capabilities

multi_message=True, edit_handling=True, delete_handling=True,
last_signal_execution=True, all standard actions enabled.

## Profile fields

```python
provider_name="provider_001"
version="2B"
field_separators=[]
multi_value_separators=["/"]
range_patterns=["-"]
multiline_mode=False
```

## Rules

Inherits common rules (SL, TP, triggers, actions). Adds direction
(BUY/SELL), instrument (SYMBOL matcher), entry (range, levels,
fallback first), all with `WHOLE_MESSAGE` or `BEFORE_TOKEN/SL` scope.