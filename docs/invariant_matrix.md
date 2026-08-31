| Invariant | Source | Existing/Added | Test | Status |
|---|---|---|---|---|
| BUY SL < entry_price | Design §20 / domain | Existing (enforced) | test_invalid_buy_sl_not_less_than_entry | Enforced |
| SELL SL > entry_price | Design §20 / domain | Existing (enforced) | test_invalid_buy_sl_not_less_than_entry (SELL analog) | Enforced |
| BUY TP >= entry, ascending, no duplicates | Design §20 / domain | Existing (enforced) | test_buy_tp_ascending_violation, test_buy_tp_duplicate_violates_ordering_first | Enforced |
| SELL TP <= entry, descending, no duplicates | Design §20 / domain | Existing (enforced) | test_sell_tp_descending_violation, test_sell_tp_duplicate_violates_ordering_first | Enforced |
| SINGLE requires entry_price | Design §20 / domain | Existing (enforced) | test_invalid_single_without_price | Enforced |
| RANGE requires entry_range + entry_price=None | Design §20 / domain | Existing (enforced) | test_invalid_single_without_price analog | Enforced |
| RANGE low <= high (when both present) | Design §20 / domain | Existing (enforced) | test_range_low_less_than_high (in domain); test_price_range_violates_low_high (invariants) | Enforced |
| MULTIPLE non-empty + ordered ascending | Design §20 / domain | Existing (enforced) | test_multiple_entry_levels, test_multiple_ascending_violation (invariants) | Enforced |
| MARKET entry_price must be None | Design §20 / domain | Existing (enforced) | test_invalid_market_has_price | Enforced |
| AMBIGUOUS must have DRAFT lifecycle | Design §20 / domain | Existing (enforced) | test_ambiguous_requires_draft | Enforced |
| UNSPECIFIED preserved (no default to MARKET) | Design §1.5 / §3.7.5 | Existing (enforced by explicit trigger) | test_explicit_unspecified_trigger | Enforced |
| Lifecycle: CANCELLED/ARCHIVED terminal | Design §14 / §20 | Added (pure function) | test_cancelled_to_active_invalid, test_expired_to_active_invalid, test_archived_is_terminal, test_cancelled_to_archived_valid, test_expired_to_archived_valid | Enforced (pure function) |
| Lifecycle: no CANCELLED/EXPIRED -> ACTIVE | Design §20 | Added (pure function) | test_cancelled_to_active_invalid, test_expired_to_active_invalid | Enforced (pure function) |
| Lifecycle: ARCHIVED is terminal | Design §20 | Added (pure function) | test_archived_is_terminal | Enforced (pure function) |
| Lifecycle: DRAFT -> ACTIVE/CANCELLED valid | Design §14 | Added (pure function) | test_draft_to_active_valid, test_active_to_cancelled_valid | Enforced (pure function) |
| Revision: first revision previous_id = None | Design §3.12 / §20 | Added (pure function) | test_first_revision_none_previous, test_first_revision_with_previous_invalid, test_revision_after_first_requires_previous | Enforced (pure function) |
| Revision: positive revision_number | Design §3.12 / §20 | Added (pure function) | test_positive_revision_number | Enforced (pure function) |
| Revision: revision_id != logical_signal_id | Design §3.12 / §20 | Added (pure function) | test_revision_id_must_not_equal_logical | Enforced (pure function) |
| RANGE: SL must not fall inside range | Design §20 / §9 | Intentionally deferred | — | Deferred (complex range strategies deferred) |
| Event sequence: CREATED first; REVISION requires previous; chain contiguous | Design §12 / §20 | Ambiguous / deferred | — | Deferred (requires embedded event/revision chain access beyond pure structural checks; event layer deferred) |
| Identity: logical_signal_id independent of mutable content | Design §11 / §3.1 | Structural (enforced by separate objects) | test_identity_independent_of_content | Enforced (by architecture) |
| Deep immutability (frozen tuple collections) | Design §24 / §20 | Existing (enforced) | test_deep_immutability, test_snapshot_immutable | Enforced |

Notes:
- All structural invariants defined in design Section 20 are either enforced in domain.py (existing), enforced via new pure functions in invariants.py (added), or deferred due to complexity/dependency requirements.
- No future-phase leakage (no parser, adapter, Telegram, broker, DB, replay, analytics, AI, strategy, risk added).
- No new dependencies added (invariants module uses standard library only).
- Cosmetic ruff SIM102 nested-if suggestions remain in invariants.py and domain.py (non-blocking style suggestions only).
