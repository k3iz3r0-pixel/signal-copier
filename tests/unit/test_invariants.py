"""Tests for pure structural domain invariants (Phase 1 — Step 5).

Every invariant from design Section 20 must have a test proving it holds
and a regression test proving invalid input is rejected.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from packages.signal_core.enums import (
    EntryGeometry,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.invariants import (
    validate_ambiguity_lifecycle,
    validate_geometry_entry_consistency,
    validate_lifecycle_transition,
    validate_price_direction_relationships,
    validate_revision_id_independence,
    validate_revision_sequence,
)
from packages.signal_core.value_objects import Price, PriceRange

# ------------------------------------------------------------------
# Geometry / structural consistency
# ------------------------------------------------------------------


class TestGeometryConsistency:
    def test_single_requires_price(self) -> None:
        with pytest.raises(ValueError, match="SINGLE"):
            validate_geometry_entry_consistency(EntryGeometry.SINGLE, None, None, ())

    def test_range_requires_range(self) -> None:
        with pytest.raises(ValueError, match="RANGE"):
            validate_geometry_entry_consistency(EntryGeometry.RANGE, None, None, ())

    def test_range_low_less_than_high(self) -> None:
        with pytest.raises(ValueError, match="low"):
            validate_geometry_entry_consistency(
                EntryGeometry.RANGE,
                None,
                PriceRange(
                    low=Price(value=Decimal(200)), high=Price(value=Decimal(100))
                ),
                (),
            )

    def test_multiple_requires_non_empty(self) -> None:
        with pytest.raises(ValueError, match="MULTIPLE"):
            validate_geometry_entry_consistency(EntryGeometry.MULTIPLE, None, None, ())

    def test_market_requires_none_price(self) -> None:
        with pytest.raises(ValueError, match="MARKET"):
            validate_geometry_entry_consistency(
                EntryGeometry.MARKET,
                Price(value=Decimal(100)),
                None,
                (),
            )

    def test_multiple_ordered_ascending(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            validate_geometry_entry_consistency(
                EntryGeometry.MULTIPLE,
                None,
                None,
                (Price(value=Decimal(200)), Price(value=Decimal(150))),
            )


# ------------------------------------------------------------------
# Price direction relationships
# ------------------------------------------------------------------


class TestPriceDirectionRelationships:
    def test_buy_sl_not_less_than_entry(self) -> None:
        with pytest.raises(ValueError, match="BUY"):
            validate_price_direction_relationships(
                TradeDirection.BUY,
                Price(value=Decimal(100)),
                Price(value=Decimal(100)),
                (),
            )

    def test_buy_tp_below_entry(self) -> None:
        with pytest.raises(ValueError, match="BUY"):
            validate_price_direction_relationships(
                TradeDirection.BUY,
                Price(value=Decimal(100)),
                Price(value=Decimal(95)),
                (Price(value=Decimal(90)),),
            )

    def test_buy_tp_ascending_violation(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            validate_price_direction_relationships(
                TradeDirection.BUY,
                Price(value=Decimal(100)),
                Price(value=Decimal(95)),
                (Price(value=Decimal(110)), Price(value=Decimal(105))),
            )

    def test_buy_tp_duplicate_violates_ordering_first(self) -> None:
        # Note: duplicate values inherently violate strict ascending order
        # (equal values are not strictly ascending); the invariant framework
        # checks ordering before duplicates. Both conditions are structural.
        with pytest.raises(ValueError, match="ascending"):
            validate_price_direction_relationships(
                TradeDirection.BUY,
                Price(value=Decimal(100)),
                Price(value=Decimal(95)),
                (Price(value=Decimal(100)), Price(value=Decimal(100))),
            )

    def test_sell_sl_not_greater_than_entry(self) -> None:
        with pytest.raises(ValueError, match="SELL"):
            validate_price_direction_relationships(
                TradeDirection.SELL,
                Price(value=Decimal(100)),
                Price(value=Decimal(100)),
                (),
            )

    def test_sell_tp_above_entry(self) -> None:
        with pytest.raises(ValueError, match="SELL"):
            validate_price_direction_relationships(
                TradeDirection.SELL,
                Price(value=Decimal(100)),
                Price(value=Decimal(105)),
                (Price(value=Decimal(105)),),
            )

    def test_sell_tp_descending_violation(self) -> None:
        with pytest.raises(ValueError, match="descending"):
            validate_price_direction_relationships(
                TradeDirection.SELL,
                Price(value=Decimal(100)),
                Price(value=Decimal(105)),
                (Price(value=Decimal(95)), Price(value=Decimal(99))),
            )

    def test_sell_tp_duplicate_violates_ordering_first(self) -> None:
        # Note: duplicate values inherently violate strict descending order
        with pytest.raises(ValueError, match="descending"):
            validate_price_direction_relationships(
                TradeDirection.SELL,
                Price(value=Decimal(100)),
                Price(value=Decimal(105)),
                (Price(value=Decimal(100)), Price(value=Decimal(100))),
            )


# ------------------------------------------------------------------
# Ambiguity / lifecycle structural invariants
# ------------------------------------------------------------------


class TestAmbiguityLifecycle:
    def test_ambiguous_requires_draft(self) -> None:
        validate_ambiguity_lifecycle(SignalStatus.AMBIGUOUS, LifecycleState.DRAFT)

    def test_ambiguous_active_invalid(self) -> None:
        with pytest.raises(ValueError, match="DRAFT"):
            validate_ambiguity_lifecycle(SignalStatus.AMBIGUOUS, LifecycleState.ACTIVE)

    def test_complete_active_valid(self) -> None:
        validate_ambiguity_lifecycle(SignalStatus.COMPLETE, LifecycleState.ACTIVE)


# ------------------------------------------------------------------
# Lifecycle transition structural invariants
# ------------------------------------------------------------------


class TestLifecycleTransition:
    def test_draft_to_active_valid(self) -> None:
        validate_lifecycle_transition(LifecycleState.DRAFT, LifecycleState.ACTIVE)

    def test_active_to_cancelled_valid(self) -> None:
        validate_lifecycle_transition(LifecycleState.ACTIVE, LifecycleState.CANCELLED)

    def test_cancelled_to_active_invalid(self) -> None:
        with pytest.raises(ValueError, match="ACTIVE"):
            validate_lifecycle_transition(
                LifecycleState.CANCELLED, LifecycleState.ACTIVE
            )

    def test_expired_to_active_invalid(self) -> None:
        with pytest.raises(ValueError, match="ACTIVE"):
            validate_lifecycle_transition(LifecycleState.EXPIRED, LifecycleState.ACTIVE)

    def test_cancelled_to_archived_valid(self) -> None:
        validate_lifecycle_transition(LifecycleState.CANCELLED, LifecycleState.ARCHIVED)

    def test_expired_to_archived_valid(self) -> None:
        validate_lifecycle_transition(LifecycleState.EXPIRED, LifecycleState.ARCHIVED)

    def test_archived_is_terminal(self) -> None:
        with pytest.raises(ValueError, match="ARCHIVED"):
            validate_lifecycle_transition(
                LifecycleState.ARCHIVED, LifecycleState.CANCELLED
            )

    def test_initial_cancelled_invalid(self) -> None:
        # Initial state (previous_state = None) cannot be terminal without context
        # The structural invariant: CANCELLED without previous context is invalid.
        # Note: this is interpreted as "initial state must not be CANCELLED/ARCHIVED/EXPIRED"
        # because lifecycle sequence requires a prior non-terminal state.
        with pytest.raises(ValueError):
            validate_lifecycle_transition(None, LifecycleState.CANCELLED)


# ------------------------------------------------------------------
# Revision structural invariants
# ------------------------------------------------------------------


class TestRevisionSequence:
    def test_first_revision_none_previous(self) -> None:
        validate_revision_sequence(1, None)

    def test_first_revision_with_previous_invalid(self) -> None:
        with pytest.raises(ValueError, match="First revision"):
            validate_revision_sequence(1, UUID("12345678-1234-5678-1234-567812345678"))

    def test_revision_after_first_requires_previous(self) -> None:
        with pytest.raises(ValueError, match="previous_revision_id"):
            validate_revision_sequence(2, None)

    def test_positive_revision_number(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            validate_revision_sequence(0, UUID("12345678-1234-5678-1234-567812345678"))

    def test_revision_id_independence(self) -> None:
        rev_id = uuid4()
        logical_id = uuid4()
        validate_revision_id_independence(rev_id, logical_id)

    def test_revision_id_must_not_equal_logical(self) -> None:
        same = uuid4()
        with pytest.raises(ValueError, match="independent"):
            validate_revision_id_independence(same, same)
