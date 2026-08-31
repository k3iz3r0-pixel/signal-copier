"""Pure structural domain invariants (Phase 1 — Step 5).

All invariants are deterministic pure functions with no external state,
no mutable collections, and no broker/provider/execution semantics.
"""

from __future__ import annotations

from uuid import UUID

from packages.signal_core.enums import (
    EntryGeometry,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.value_objects import Price, PriceRange

# ------------------------------------------------------------------
# Geometry / structural invariants (authoritative from design Section 20)
# ------------------------------------------------------------------


def validate_geometry_entry_consistency(
    geometry: EntryGeometry,
    entry_price: Price | None,
    entry_range: PriceRange | None,
    entry_levels: tuple,
) -> None:
    """Validate entry geometry / field consistency.

    Rules (design Section 20):
    - SINGLE: entry_price must be present (Price, not None)
    - RANGE: entry_range must be present; entry_price must be None
    - MULTIPLE: entry_levels must be non-empty; entry_price must be None
    - MARKET: entry_price must be None (unknown at signal time)
    """
    if geometry == EntryGeometry.SINGLE:
        if entry_price is None:
            raise ValueError("SINGLE geometry requires a non-None entry_price")
    elif geometry == EntryGeometry.RANGE:
        if entry_range is None:
            raise ValueError("RANGE geometry requires a non-None entry_range")
        if entry_price is not None:
            raise ValueError("RANGE geometry requires entry_price to be None")
        # Low <= high when both present (design Section 20; enforced here)
        if (
            entry_range.low is not None
            and entry_range.high is not None
            and entry_range.low.value > entry_range.high.value
        ):
            raise ValueError(
                "RANGE invariant violated: low.value must be <= high.value"
            )
    elif geometry == EntryGeometry.MULTIPLE:
        if len(entry_levels) == 0:
            raise ValueError("MULTIPLE geometry requires non-empty entry_levels")
        if entry_price is not None:
            raise ValueError("MULTIPLE geometry requires entry_price to be None")
        # Ordered ascending (design Section 20; enforced here)
        for i in range(1, len(entry_levels)):
            prev = entry_levels[i - 1].value  # type: ignore[index]
            curr = entry_levels[i].value  # type: ignore[index]
            if curr <= prev:
                raise ValueError(
                    "MULTIPLE entry_levels must be strictly ordered (ascending)"
                )
    elif geometry == EntryGeometry.MARKET and entry_price is not None:
        raise ValueError("MARKET geometry requires entry_price to be None")


# ------------------------------------------------------------------
# Price relationship invariants (authoritative from design Section 20)
# ------------------------------------------------------------------


def validate_price_direction_relationships(
    direction: TradeDirection,
    entry_price: Price | None,
    stop_loss: Price | None,
    take_profit_targets: tuple,
) -> None:
    """Validate SL/TP direction and ordering invariants.

    Rules (design Section 20):
    - BUY: SL.value < entry_price.value (when both present)
    - BUY: TP targets >= entry_price.value; strictly ascending; no duplicates
    - SELL: SL.value > entry_price.value (when both present)
    - SELL: TP targets <= entry_price.value; strictly descending; no duplicates
    """
    # BUY SL < entry
    if (
        direction == TradeDirection.BUY
        and entry_price is not None
        and stop_loss is not None
        and stop_loss.value >= entry_price.value
    ):
        raise ValueError(
            "BUY direction invariant violated: stop_loss.value must be < entry_price.value"
        )
    # SELL SL > entry
    if (
        direction == TradeDirection.SELL
        and entry_price is not None
        and stop_loss is not None
        and stop_loss.value <= entry_price.value
    ):
        raise ValueError(
            "SELL direction invariant violated: stop_loss.value must be > entry_price.value"
        )
    # BUY TP >= entry; ascending; no duplicates
    if direction == TradeDirection.BUY and entry_price is not None:
        for tp in take_profit_targets:
            if tp.value < entry_price.value:
                raise ValueError(
                    "BUY direction invariant violated: TP value must be >= entry_price.value"
                )
        for i in range(1, len(take_profit_targets)):
            prev = take_profit_targets[i - 1].value  # type: ignore[index]
            curr = take_profit_targets[i].value  # type: ignore[index]
            if curr <= prev:
                raise ValueError(
                    "BUY TP ordering invariant violated: TP targets must be strictly ascending"
                )
        unique_tps = {tp.value for tp in take_profit_targets}  # type: ignore[index]
        if len(unique_tps) != len(take_profit_targets):
            raise ValueError("BUY TP targets must contain no duplicate values")
    # SELL TP <= entry; descending; no duplicates
    if direction == TradeDirection.SELL and entry_price is not None:
        for tp in take_profit_targets:
            if tp.value > entry_price.value:
                raise ValueError(
                    "SELL direction invariant violated: TP value must be <= entry_price.value"
                )
        for i in range(1, len(take_profit_targets)):
            prev = take_profit_targets[i - 1].value  # type: ignore[index]
            curr = take_profit_targets[i].value  # type: ignore[index]
            if curr >= prev:
                raise ValueError(
                    "SELL TP ordering invariant violated: TP targets must be strictly descending"
                )
        unique_tps = {tp.value for tp in take_profit_targets}  # type: ignore[index]
        if len(unique_tps) != len(take_profit_targets):
            raise ValueError("SELL TP targets must contain no duplicate values")


# ------------------------------------------------------------------
# Ambiguity / completeness structural invariants (design Section 20)
# ------------------------------------------------------------------


def validate_ambiguity_lifecycle(
    state: SignalStatus, lifecycle: LifecycleState
) -> None:
    """Ambiguous signals must remain in DRAFT lifecycle state (design Section 20).

    This is a structural invariant: AMBIGUOUS status requires DRAFT state.
    """
    if state == SignalStatus.AMBIGUOUS and lifecycle != LifecycleState.DRAFT:
        raise ValueError(
            "Ambiguous signals must have lifecycle_state DRAFT per approved design"
        )


# ------------------------------------------------------------------
# Lifecycle transition structural invariants (design Section 20 / 14)
# ------------------------------------------------------------------

VALID_LIFECYCLE_SEQUENCE = {
    LifecycleState.DRAFT,
    LifecycleState.ACTIVE,
    LifecycleState.CANCELLED,
    LifecycleState.EXPIRED,
    LifecycleState.ARCHIVED,
}

# Minimal transition matrix (authoritative from design Section 14):
# DRAFT -> ACTIVE -> CANCELLED / EXPIRED -> ARCHIVED
# CANCELLED or EXPIRED are terminal except for ARCHIVED.
# No transition from CANCELLED or EXPIRED back to ACTIVE.
VALID_LIFECYCLE_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.DRAFT: {LifecycleState.ACTIVE, LifecycleState.CANCELLED},
    LifecycleState.ACTIVE: {
        LifecycleState.CANCELLED,
        LifecycleState.EXPIRED,
        LifecycleState.ARCHIVED,
    },
    LifecycleState.CANCELLED: {LifecycleState.ARCHIVED},
    LifecycleState.EXPIRED: {LifecycleState.ARCHIVED},
    LifecycleState.ARCHIVED: set(),  # terminal; no further transitions
}


def validate_lifecycle_transition(
    previous_state: LifecycleState | None,
    new_state: LifecycleState,
) -> None:
    """Validate lifecycle transition is allowed by approved design Section 14/20.

    Rules:
    - DRAFT -> ACTIVE, CANCELLED allowed
    - ACTIVE -> CANCELLED, EXPIRED, ARCHIVED allowed
    - CANCELLED -> ARCHIVED allowed (terminal path)
    - EXPIRED -> ARCHIVED allowed (terminal path)
    - ARCHIVED -> no transition allowed (terminal)
    - CANCELLED or EXPIRED -> ACTIVE: invalid (forbidden back-transition)
    - ARCHIVED -> CANCELLED/ARCHIVED: invalid (already terminal)
    """
    if previous_state is None:
        # First state must be DRAFT or ACTIVE; CANCELLED/ARCHIVED/EXPIRED
        # without a prior state is only valid for revisions that reference
        # a previous revision (not enforced here; handled by revision link check).
        # For structural purposes, initial states must not be terminal without context.
        if new_state in {
            LifecycleState.CANCELLED,
            LifecycleState.EXPIRED,
            LifecycleState.ARCHIVED,
        }:
            raise ValueError(
                "Lifecycle state CANCELLED, EXPIRED, or ARCHIVED requires a previous state context (revision/reference); cannot be initial"
            )
        return

    allowed = VALID_LIFECYCLE_TRANSITIONS.get(previous_state, set())
    if new_state not in allowed:
        # Special case: terminal back-transition check
        if (
            previous_state in {LifecycleState.CANCELLED, LifecycleState.EXPIRED}
            and new_state == LifecycleState.ACTIVE
        ):
            raise ValueError(
                "Lifecycle transition invalid: CANCELLED or EXPIRED cannot transition back to ACTIVE"
            )
        if (
            previous_state == LifecycleState.ARCHIVED
            and new_state != LifecycleState.ARCHIVED
        ):
            raise ValueError(
                "Lifecycle transition invalid: ARCHIVED is terminal; no transition from ARCHIVED allowed"
            )
        raise ValueError(
            f"Lifecycle transition invalid: {previous_state.value} -> {new_state.value} is not permitted"
        )


# ------------------------------------------------------------------
# Revision structural invariants (design Section 20 / 3.12 / 13)
# ------------------------------------------------------------------


def validate_revision_sequence(
    revision_number: int, previous_revision_id: UUID | None
) -> None:
    """Validate revision number and previous link consistency.

    Rules:
    - revision_number must be >= 1.
    - First revision (revision_number == 1) must have previous_revision_id = None.
    - Any revision after first must have previous_revision_id set (UUID).
    """
    if revision_number < 1:
        raise ValueError("revision_number must be positive int (>=1)")
    if revision_number == 1 and previous_revision_id is not None:
        raise ValueError(
            "First revision (revision_number == 1) must have previous_revision_id = None"
        )
    if revision_number > 1 and previous_revision_id is None:
        raise ValueError("Revision number > 1 requires a non-None previous_revision_id")


def validate_revision_id_independence(
    revision_id: UUID, logical_signal_id: UUID
) -> None:
    """Revision identity must be independent of logical signal identity.
    This is a structural separation invariant (design Section 3.12).
    """
    if revision_id == logical_signal_id:
        raise ValueError(
            "revision_id must be independent of logical_signal_id; revision identity must not equal logical identity"
        )


# ------------------------------------------------------------------
# Signal identity structural invariants (design Section 3.1 / 11)
# ------------------------------------------------------------------


def validate_identity_independence_from_content(
    logical_signal_id: UUID,
    fingerprint_reference: str,
) -> None:
    """Structural separation: logical identity never derived from content fingerprint.

    This pure function validates the conceptual separation defined in
    design Section 11 (Identity Strategy). It does not enforce fingerprint
    equality (that is handled by SignalRevision); it validates that identity
    and fingerprint are separate concepts and identity is not a hash of content.

    Since logical_signal_id is a UUID and fingerprint is a hex string,
    equality between them would indicate an architecture violation.
    """
    # The structural rule: logical_signal_id must never equal the fingerprint string
    # (they are different types, but comparing the UUID string representation to
    # fingerprint would reveal an incorrect derivation policy).
    if str(logical_signal_id) == fingerprint_reference:
        raise ValueError(
            "logical_signal_id must not be derived from fingerprint; identity must remain independent of mutable content"
        )
