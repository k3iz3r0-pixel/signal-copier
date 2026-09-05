# Provider 003 — Bitcoin-style, no decimals, LONG/SHORT keywords (§21.3).

## Structural family

Crypto-style integer prices, direction expressed as LONG/SHORT
(canonicalized to BUY/SELL by the rule's explicit `canonical` param with the
raw text preserved in evidence), and crypto symbols via the alias table.

## Examples

- `LONG BTC 60000 SL 58000 TP 65000` → PARSED (direction=BUY, canonical_alias=LONG→BUY)
- `SHORT ETH 3000 SL 3100 TP 2800` → PARSED (direction=SELL)

## Capabilities

multi_message=True, edit_handling=True, delete_handling=True,
last_signal_execution=True.

## Profile fields

```python
provider_name="provider_003"
version="2B"
field_separators=[]
multi_value_separators=["/"]
range_patterns=["-"]
multiline_mode=False
symbol_aliases=[["BTC", "BTC"], ["ETH", "ETH"]]
```

## Rules

Inherits common rules. Direction uses `LITERAL` matcher with a `canonical`
param: `value="LONG", canonical="BUY"` and `value="SHORT", canonical="SELL"`.
Instrument is the SYMBOL matcher. Entry has range + first-number rules.