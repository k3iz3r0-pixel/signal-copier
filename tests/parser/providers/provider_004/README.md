# Provider 004 — Emoji field markers, line-structured (§21.4).

## Structural family

Each field is introduced by a dedicated emoji marker on its own line:
🎯 entry, 🛑 SL, 💰 TP. Header line carries a status emoji + direction +
hashtag symbol ("🟢 BUY #EURUSD" — "#" is stripped as markdown syntax).
Matches are LINE-scoped, so a marker can never capture a number from
another line. This is the first onboarded provider whose field syntax is
non-keyword decoration entirely.

## Examples

- `🟢 BUY #EURUSD\n🎯 1.1000\n🛑 1.0950\n💰 1.1100` → PARSED
- `🔴 SELL #EURUSD\n🎯 1.2500\n🛑 1.2550\n💰 1.2400\n💰 1.2350` → PARSED (two TP levels)
- `🟢 BUY #EURUSD\n🎯 1.1000\n🎯 1.1050\n...` → MALFORMED (conflicting entries preserved)
- `🛑 2%` line → SL NOT bound (percent can never become a price; the value
  is preserved as an unbound PRICE candidate)

## Capabilities

Standard set (multi_message, edit/delete handling, actions enabled;
profit_close / move_sl_conditional / trailing / multi_signal off).

## Profile fields

```python
provider_name = "provider_004"
version = "2B"
field_separators = []
multi_value_separators = ["/"]
range_patterns = ["-"]
multiline_mode = True
symbol_aliases = [["EURUSD", "EURUSD"], ["GBPUSD", "GBPUSD"], ["XAUUSD", "XAUUSD"]]
```

## Rules

Inherits common rules (actions; keyword-form SL/TP remain available).
Own rules: direction LITERAL BUY/SELL, instrument SYMBOL, and three
LINE-scoped REGEX rules capturing the number after each emoji marker.
