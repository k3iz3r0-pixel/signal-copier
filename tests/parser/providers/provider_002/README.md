# Provider 002 — Multiline, em-dash field separators (Design §21.2).

## Structural family

Line-based layout with em-dash separators between the field keyword and its
value ("SL — 1.0950"). The whitespace-collapse step of the fixed §5.5.1
pipeline yields a single-line normalized view in which the em-dash survives
as the canonical field separator (after canonicalize_separators). The em-dash
SL/TP rules MASK the common keyword rules via renamed overrides (§12.5.7) —
exercising the override mechanism end to end.

## Examples

```
BUY EURUSD
ENTRY 1.1000
SL — 1.0950
TP — 1.1100
```

→ PARSED (entry=1.1000, SL=1.0950, TP=1.1100).

## Capabilities

multi_message=True, edit_handling=True, delete_handling=True,
last_signal_execution=True.

## Profile fields

```python
provider_name="provider_002"
version="2B"
field_separators=["—"]
multi_value_separators=["/"]
range_patterns=["-"]
multiline_mode=True
```

## Rules

Inherits common rules; overrides `common.sl.number` and `common.tp.number`
with the em-dash REGEX matchers `p002.sl.emdash` and `p002.tp.emdash`.
Direction (BUY/SELL), instrument, entry (after ENTRY keyword) are
provider-specific.