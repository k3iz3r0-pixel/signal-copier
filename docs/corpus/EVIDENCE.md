# Phase 2C — Real-Provider Corpus: Classification, Axes, Evidence Model

Authoritative input: `docs/corpus/real-messages.md` (owner-supplied raw
examples, 379 lines, 32 messages). Everything below is derived from that
file plus engine probes (`/tmp/opencode/probe_2c.py`, engine unchanged).
No provider behavior was invented; where the corpus does not determine a
semantic, it is recorded as deferred/unknown.

Message numbering `M1..M32` follows file order (blocks separated by blank
lines; line numbers refer to `real-messages.md`).

## STEP 1 — Classification (every message)

| ID | Lines | Type | Blocks | Executable core | Notes |
|----|-------|------|--------|-----------------|-------|
| M1 | 1–10 | EVENT | 1 | none | closed-trade ticket block; SL-hit; thousands-space profit `-1 015$` |
| M2 | 14–22 | NEW_SIGNAL | 1 | SELL XAUUSD e2656.00 sl2659.99 tp2647.79 | bracket pips/Lots/RR annotations; ticket id |
| M3 | 26–38 | REPORT | 1 | none | weekly stats; per-trade `XAUUSD Buy 1.7%` lines (false-positive surface) |
| M4 | 41–48 | ACTION | 1 | MOVE_SL→2726.94 (XAUUSD Buy context) | Old SL must not bind; "moved to Breakeven" prose |
| M5 | 51–61 | NEW_SIGNAL | 1 | BUY GBPJPY limit e198.862 sl198.680 tp199.550 | `Max risk %1` unbound |
| M6 | 65–67 | COMMENTARY | 1 | none | risk prose; NO_SIGNAL expected |
| M7 | 71–91 | NEW_SIGNAL | 1 | BUY EURUSD e1.16122 sl1.16112 tp1/2/3 | Pair:/Direction: labels; BOUGHT…at; R-multiples; lot/accuracy noise |
| M8 | 97–117 | NEW_SIGNAL | 1 | SELL EURUSD e1.16186 sl1.16233 tp1/2/3 | same family as M7 |
| M9 | 121–137 | NEW_SIGNAL | 1 | BUY XAUUSD limit e4302.00 sl4273.00 tp×3 | long analysis prose + `300/250 region` noise |
| M10 | 141–145 | NEW_SIGNAL | 1 | BUY USDJPY e159.31 sl158.81 tp160.81 | colon labels; signature tail |
| M11 | 147–152 | NEW_SIGNAL | 1 | SELL XAUUSD e4596.00 tp×4 sl4601 | TP-before-SL order |
| M12 | 154–160 | NEW_SIGNAL | 1 | BUY XAUUSD range 4267/4270 sl4257 tp×3 | slash range |
| M13 | 163–170 | NEW_SIGNAL | 1 | SELL XAUUSD range 4066/4070 sl4097 tp×3 | + "To open" tail |
| M14 | 173–182 | NEW_SIGNAL | 1 | SHORT GOLD zone 4424-4434 stop4439 tgt4421/4416 | hyphen zone range; `Target N:` ordinals — DEFERRED (batch 2) |
| M15 | 185–192 | NEW_SIGNAL | 1 | BUY GOLD/XAUUSD range 4423.5-4425.5 sl4417 tp1/2 | markdown bold; hyphen-space range — DEFERRED (batch 2) |
| M16 | 195–198 | ACTION (+event) | 1 | MOVE_SL→4420 (GOLD) | `TP1 HIT` event prose; `Move SL at` phrasing |
| M17 | 201–204 | NEW_SIGNAL | 1 | BUY GOLD e4425 | two-line core |
| M18 | 204–212 | NEW_SIGNAL | 1 | BUY XAUUSD now e4472.443 sl4459.578 tp4532.556 | `Entery:` typo label — DEFERRED (batch 2) |
| M19 | 215–247 | NEW_SIGNAL | 4 | — (multi-block) | 2 stop orders × 2 feed copies; multi-block → conflicts (deferred) |
| M20 | 251–267 | ACTION + NEW_SIGNAL | 3 | — (mixed) | trigger+cancel events + 2 new stop blocks (deferred) |
| M21 | 272 | NEW_SIGNAL | 1 | BUY XAUUSD limit e4342.72 sl4324.74 (no TP) | lowercase labels; PARTIAL w/o TP |
| M22 | 275–279 | NEW_SIGNAL | 1 | SELL US30 sl52953.2 tp×2 (no entry) | PARTIAL entry_pending; `Stop` label is SL not trigger |
| M23 | 282–286 | NEW_SIGNAL | 1 | SELL XAGUSD e65.1950 sl67.0731 tp61.3857 | `@` level separator |
| M24 | 288–296 | NEW_SIGNAL | 1 | SELL XAUUSD now e4133.00 tp4076.00 sl4152.00 | lowercase Tp/Sl; `Risk 1%` unbound |
| M25 | 299–302 | NEW_SIGNAL | 1 | SELL GOLD sl4168.00 tp4088.00 (no entry) | PARTIAL entry_pending |
| M26 | 304–307 | NEW_SIGNAL | 1 | SELL GOLD e4103.210 sl4112.757 tp1/2 | `@` entry; Tp1/Tp2 |
| M27 | 309–327 | NEW_SIGNAL | 1 | SELL EURUSD limit e1.17725 sl1.17825 tp1/2 | forecast prose; "now" = temporal adverb (NOT market) |
| M28 | 331 | AMBIGUOUS | 1 | — | `EJ` symbol unmappable (no corpus expansion); `Buying` progressive verb |
| M29 | 334–338 | NEW_SIGNAL | 1 | SELL EURUSD e1.1624 tp1.1591 sl1.1646 | bare `Take`/`Stop` labels — DEFERRED (batch 2) |
| M30 | 344–348 | NEW_SIGNAL | 1 | SELL GBPCHF now e1.08280 tp1.07750 sl1.08500 | `SELL NOW at`; pip annotations |
| M31 | 352–357 | NEW_SIGNAL | 1 | BUY AUDJPY e100.814 sl100.564 tp101.064 | emoji annotations; `@Sp25PIPS` handle |
| M32 | 359–374 | EVENT | 1 | none | completion report; `MANUALLY CLOSE WITH 1150 PIPS` — DEFERRED (event semantics) |

Totals: NEW_SIGNAL 22 · ACTION 2 (M4, M16) · EVENT 2 (M1, M32) · REPORT 1 (M3)
· COMMENTARY 1 (M6) · AMBIGUOUS 1 (M28) · multi-block 2 (M19, M20).

## STEP 2 — Structural axes matrix (corpus evidence)

| Axis | Evidence | Coverage in batch 1 |
|------|----------|---------------------|
| direction vocabulary | BUY/SELL (M2,M10,M11,M12,M13,M17,M22,M31); buy/sell lowercase (M5,M21,M24); Long/Short (M7,M8); BOUGHT/SOLD (M7,M8); SHORT (M14, deferred) | 013(RE-gated), 014, 015, 016, 017 |
| instrument placement | before direction (M2); with direction line (M10,M11,M31); `Pair:` label (M7,M8); own line (M9,M17); `Instrument:` (M19) | 013–017 |
| market/NOW syntax | `sell now` (M24); `SELL NOW at` (M30); `Buy Now` (M18, deferred); "now" as adverb (M27 → must NOT map to MARKET) | 014 (M24), 017 (M30; M27 guarded by FORBIDS LIMIT) |
| limit | `buy limit` (M5,M9,M21); `SELL LIMIT now at` (M27) | 014, 017 (common) |
| stop (order) | `SELL STOP`/`BUY STOP` (M19,M20) | deferred (multi-block family) |
| single entry | M2,M5,M7–M11,M17,M21,M23–M27,M30,M31 | all batch families |
| entry range | slash `4267/4270` (M12), `4066/4070` (M13); hyphen zone `4424-4434` (M14, deferred); hyphen-space `4423.5- 4425.5` (M15, deferred) | 014 (slash → PriceRange/RANGE) |
| range separators | `/` (M12,M13), `-` (M14,M15 deferred) | 014 `range_patterns=["-","/"]` |
| Entry/Entery/@ labels | `Entry:` (M2), `Entry ` (M5,M9,M29), `Entery:` typo (M18 deferred), `@` (M23,M26), prose `at` (M7,M8,M16,M27,M28,M30) | 013 (Entry:), 014 (label/@-free), 016 (@), 017 (at) |
| SL forms | `SL:` (M2), `SL ` plain (M7,M8,M12,M13,M31), lowercase `sl` (M21,M24), `Stop loss:` (M9,M22), `Stop:` (M14 deferred), `Stop ` (M29 deferred), `SL @` (M23) | 013(Entry: style), 014, 015, 016, 017 |
| TP forms | `TP:` (M2,M30), `TP ` (M5,M10–M13,M23–M25), `Tp ` lowercase (M12,M13,M24), `Tp1/Tp2` (M26), `TP1/2/3` (M7,M8; M15,M32 deferred), `Take profit:` (M9,M22), `Take `/`Target N:` (M29/M14 deferred) | 013,014,015,016,017 |
| ordinal TP | TP1/TP2/TP3 (M7,M8), Tp1/Tp2 (M26), Target 1/2 (M14) | 015, 016, 017 (014 via repeated labels) |
| repeated unlabeled TP | M11 (4×), M12/M13 (3×), M9 (3× `Take profit:`), M22 (2×) | 014 |
| risk/lots/RR/pips fields | `[Lots: 2.50]`, `[39.9 Pips]`, `RR: 2.06` (M2); `[1 Pips]`, `[2.5R]`, `Position Size: 2%`, `$1K … 100 Lots` (M7,M8); `Max risk %1` (M5); `Risk 1%` (M24); `(-25pips)` (M31); `(+53 pips)` (M30) | ALL unbound by contract (no fields); verified never bound |
| action/update vocabulary | `Modified`/`Moved SL`/`New SL:` (M4); `Move SL at` (M16); `MOVE SL TO` (none in corpus) | 013 (New SL), 017 (Move SL at) |
| breakeven | `Stop moved to Breakeven` (M4, prose duplicate of the numeric move) | 013 (documented: numeric new-SL is the operative instruction) |
| close vocabulary | `CLOSED` (M1); `MANUALLY CLOSE WITH 1150 PIPS` (M32) | M1 NO_SIGNAL ✓; M32 DEFERRED (spurious CLOSE action) |
| pending lifecycle | `sell stop order was triggered` / `Delete the buy stop order` (M20) | DEFERRED (mixed multi-block) |
| reports/statistics | M3 (wins/losses/%); M1 profit/exit; M32 RR | M1/M3 NO_SIGNAL under 013 ✓; M32 deferred |
| commentary/noise | M6; prose in M9/M27; disclaimers (M19,M27); links/handles (M3,M31) | negative tests in 013/014/017 |
| multi-block messages | M19 (4 blocks, 2 duplicated), M20 (actions + 2 blocks) | DEFERRED (no reconstruction; conflicts surfaced — see §below) |

## STEP 3 — Evidence model (per implemented family)

For each family: raw messages are quoted VERBATIM in
`tests/fixtures/providers/provider_01{3..7}/canonical.py`; expected fields,
spans, and ambiguity expectations are asserted in the provider test suites.
Raw source spans of PRICE candidates are asserted to slice the raw text
exactly (no re-synthesis). Executable vs non-executable: NEW_SIGNAL/ACTION
cores are executable-shaped; REPORT/EVENT/COMMENTARY messages must yield
NO_SIGNAL (verified for M1/M3/M6) — outcome classification beyond
NEW_SIGNAL-vs-not is a Phase-3+ concern (§14 failure model).

## STEP 6 — Reusable vs provider-specific vs unsupported

A. Reusable generic (validated on real data; already in engine/common):
core direction-adjacent entry, symbol-adjacent entry, labeled SL/TP,
repeated-TP merge, LIMIT/STOP/MARKET triggers, NOW→MARKET canonical,
at-price entry, ordinal TP regex, slash range → PriceRange, GOLD/XAUUSD
alias, keyword gating (REQUIRES), annotation exclusion (FORBIDS OLD).

B. Provider-specific (data-only rules in the batch):
bracket-annotated ticket blocks + NEW-header gating (013);
Pair:/Direction:/BOUGHT/SOLD/R-multiple scalp cards (015);
@-separated levels (016); prose Stop loss/Take profit + "now" adverb
guard (014); `Move SL at` follow-up phrasing (017).

C. Unsupported → deferred (no fabrication):
multi-message/block reconstruction (M19, M20 — engine surfaces conflicts;
splitting is Phase-3+); close-event reports (M32 — spurious CLOSE action);
unknown symbol abbreviations (M28 `EJ` — open question #7 symbol mapping);
`Entery` typo family (M18), zone/target hyphen ranges + `Target N` (M14),
markdown GOLD/XAUUSD ranges (M15), bare Take/Stop (M29) — all batch-2
candidates; percent-only SL/TP, REVERSE, conditional if/then, locale
decimal signals — NOT PRESENT in corpus (the only % / comma-thousands
occurrences are in non-executable report/event text).

## Deferred families — exact reasons

| Family | Messages | Reason |
|--------|----------|--------|
| dual-feed stop-order blocks | M19, M20 | multi-block/duplicates; single-signal IR cannot represent 4 blocks; reconstruction prohibited (Phase-3+). Engine correctly surfaces DIRECTION+SL conflicts (verified). |
| zone/target hyphen grammar | M14 | needs own range gating (`Zone:` line) + `Target N` ordinals + `Stop:` label minus STOP-trigger false positive — batch 2 (Target-N regex capability itself verified working). |
| markdown range card | M15 | GOLD/XAUUSD pair alias + hyphen-space range + emoji ordinals — batch 2. |
| typo-label market card | M18 | `Entery:` typo + `Buy Now` — batch 2 (NOW→MARKET verified). |
| EJ abbreviation | M28 | `EJ` unmappable without provider symbol evidence (§23 open question #7); `Buying` progressive verb also undeclared. AMBIGUOUS by evidence, not by guess. |
| bare Take/Stop card | M29 | `Take`/`Stop` stopwords — batch 2 (Mike-pattern extension). |
| completion report | M32 | `MANUALLY CLOSE WITH 1150 PIPS` fires common CLOSE action → spurious executable action from a report; close-EVENT semantics not in contract → deferred. |

## Key engine facts established by probes (engine unchanged)

1. `normalize` strips `*_`~[]#>|` — bracket annotations lose their
   brackets; zone rules would absorb annotation numbers → conflicts.
   Annotation-bearing families must use REGEX-labeled field rules
   (regex sites match exactly; no zone spillover).
2. LITERAL-rule keyword candidates bypass constraint checks → gating a
   LITERAL with REQUIRES does not gate the keyword candidate. Gating
   must use REGEX rules (constraint-checked) when un-gated occurrences
   must not bind (013 NEW-gating, 017 NOW guard).
3. `entry.range` (PRICE_RANGE) claims both endpoints; §7.3 longer-match
   gives RANGE over singles. Slash ranges work via `range_patterns`.
   Engine accepts INVERTED PriceRange (low>high) without validation —
   contract observation, not exercised by any executable corpus signal.
4. `core_adjacent` reaches SYMBOL tokens only; whole-message numeric
   rules bind only symbol-adjacent numbers (M31-style entries) —
   prose numbers (M9 `300/250`) can never be hijacked by keyword-less
   whole-message rules.
5. Multi-block messages surface DIRECTION/SL conflicts (M19 verified) —
   honest failure, no silent merge.
