import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import (
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    _canonical_fingerprint,
)
from packages.signal_core.enums import (
    EventType,
    InstructionType,
)
from packages.signal_core.value_objects import (
    Price,
    ProviderSource,
)


@pytest.fixture
def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(
            provider_name="provider_alpha", signal_reference="ref-001"
        ),
    )


# =============== SIGNAL REVISION ===============

# 1. Valid revision


def test_valid_revision(identity: SignalIdentity) -> None:
    snapshot = (
        ("direction", "BUY"),
        ("entry_geometry", "SINGLE"),
        ("entry_trigger", "LIMIT"),
        ("entry_price", "1.1000"),
        ("status", "COMPLETE"),
        ("lifecycle_state", "ACTIVE"),
    )
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="dummy_fingerprint_for_structural_test",
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.revision_number == 1
    assert rev.previous_revision_id is None
    assert rev.logical_signal_id == identity.logical_signal_id


# 2. Complete canonical snapshot independently inspectable


def test_snapshot_inspectable(identity: SignalIdentity) -> None:
    snapshot = (
        ("direction", "SELL"),
        ("entry_geometry", "MARKET"),
        ("entry_trigger", "MARKET"),
        ("status", "PARTIAL"),
        ("lifecycle_state", "DRAFT"),
    )
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="fingerprint_for_snapshot",
        created_at_utc=datetime(2024, 2, 2, 0, 0, 0, tzinfo=UTC),
    )
    # Independent inspection: snapshot contains full state; no previous revision needed
    assert ("direction", "SELL") in rev.canonical_snapshot
    assert rev.previous_revision_id is not None


# 3. Immutable snapshot


def test_snapshot_immutable(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="fp",
        created_at_utc=datetime(2024, 3, 3, 0, 0, 0, tzinfo=UTC),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        rev.canonical_snapshot += (("bad", "bad"),)  # type: ignore[operator]


# 4. Revision number


def test_revision_number_valid(identity: SignalIdentity) -> None:
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=5,
        previous_revision_id=uuid4(),
        canonical_snapshot=(),
        fingerprint="fp",
        created_at_utc=datetime(2024, 4, 4, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.revision_number == 5


def test_revision_number_invalid(identity: SignalIdentity) -> None:
    with pytest.raises(ValueError, match="positive int"):
        SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=0,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="fp",
            created_at_utc=datetime(2024, 5, 5, 0, 0, 0, tzinfo=UTC),
        )


# 5. Logical identity


def test_logical_identity_stable(identity: SignalIdentity) -> None:
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("status", "COMPLETE"),),
        fingerprint="fp1",
        created_at_utc=datetime(2024, 6, 6, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=(("status", "CANCELLED"),),
        fingerprint="fp2",
        created_at_utc=datetime(2024, 7, 7, 0, 0, 0, tzinfo=UTC),
    )
    assert rev1.logical_signal_id == rev2.logical_signal_id
    assert rev1.logical_signal_id == identity.logical_signal_id


# 6. Previous revision ID non-recursive


def test_previous_revision_id_non_recursive(identity: SignalIdentity) -> None:
    prev_id = uuid4()
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=prev_id,
        canonical_snapshot=(),
        fingerprint="fp",
        created_at_utc=datetime(2024, 8, 8, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.previous_revision_id == prev_id
    # It is an identifier, not an embedded SignalRevision object
    assert not isinstance(rev.previous_revision_id, SignalRevision)


# 7. Non-recursive revision linkage


def test_revision_linkage_non_recursive(identity: SignalIdentity) -> None:
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(),
        fingerprint="fp1",
        created_at_utc=datetime(2024, 9, 9, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=(),
        fingerprint="fp2",
        created_at_utc=datetime(2024, 10, 10, 0, 0, 0, tzinfo=UTC),
    )
    # No embedded objects; only UUID references
    assert rev2.previous_revision_id == rev1.revision_id


# 8. Equality / hashing


def test_revision_equality_and_hash(identity: SignalIdentity) -> None:
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("status", "COMPLETE"),),
        fingerprint="fp",
        created_at_utc=datetime(2024, 11, 11, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=rev1.revision_id,
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("status", "COMPLETE"),),
        fingerprint="fp",
        created_at_utc=rev1.created_at_utc,
    )
    assert rev1 == rev2
    assert hash(rev1) == hash(rev2)


# 9. Fingerprint independent of revision metadata


def test_fingerprint_independent_of_metadata(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"),)
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="fp",
        event_reference_id=uuid4(),
        snapshot_version=2,
        created_at_utc=datetime(2024, 12, 12, 0, 0, 0, tzinfo=UTC),
    )
    # Changing only metadata (revision_number, previous_revision_id, event_reference_id, version, timestamp) should change fingerprint
    # But the design requires the fingerprint to match canonical content. Since the snapshot is the same, the fingerprint should be consistent.
    # We verify that fingerprint is a non-empty str and stable for same snapshot.
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=5,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="fp",
        event_reference_id=uuid4(),
        snapshot_version=3,
        created_at_utc=datetime(2024, 12, 12, 1, 0, 0, tzinfo=UTC),
    )
    # Since fingerprint is computed from snapshot, both revisions with the same snapshot get the same fingerprint
    assert rev_a.fingerprint == rev_b.fingerprint
    assert rev_a.fingerprint == rev_b.fingerprint  # same computed hash


# 10. Fingerprint deterministic (same content → same fingerprint)


def test_fingerprint_deterministic(identity: SignalIdentity) -> None:
    snapshot = (("status", "CANCELLED"), ("direction", "BUY"))
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=3,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="deterministic_fp",
        created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=3,
        previous_revision_id=rev1.previous_revision_id,
        canonical_snapshot=snapshot,
        fingerprint="deterministic_fp",
        created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    # Note: the design specifies fingerprint is computed from canonical_snapshot; here we use the same string for test.
    # The key invariant is that fingerprint is a required str and stable for same snapshot.
    assert rev1.fingerprint == rev2.fingerprint


# 11. Fingerprint computed from snapshot (empty input ignored, computed value set)


def test_fingerprint_computed_ignores_empty_string(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="",
        created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint != ""
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# 12. Invalid snapshot rejected (not tuple)


def test_invalid_snapshot_not_tuple(identity: SignalIdentity) -> None:
    with pytest.raises(TypeError, match="frozen tuple"):
        SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot={"bad": "snapshot"},
            fingerprint="fp",
            created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        )


# =============== SIGNAL EVENT ===============

# 18. Valid event


def test_valid_event(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.CREATED,
        timestamp_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert event.event_type == EventType.CREATED


# 19. Event type


def test_event_type_members(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.CANCELLED,
        timestamp_utc=datetime(2025, 2, 2, 0, 0, 0, tzinfo=UTC),
    )
    assert event.event_type == EventType.CANCELLED


# 20. Event identity


def test_event_identity_reference_only(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.REVISED,
        timestamp_utc=datetime(2025, 3, 3, 0, 0, 0, tzinfo=UTC),
    )
    assert event.signal_identity.logical_signal_id == identity.logical_signal_id
    # Event does not embed full Signal
    assert not hasattr(event, "instrument")


# 21. Event timestamp


def test_event_timestamp_utc(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.CREATED,
        timestamp_utc=datetime(2025, 4, 4, 12, 30, 0, tzinfo=UTC),
    )
    assert event.timestamp_utc.tzinfo is not None
    assert event.timestamp_utc.utcoffset().total_seconds() == 0


# 22. Event payload


def test_event_payload_immutable(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.SL_MOVED,
        timestamp_utc=datetime(2025, 5, 5, 0, 0, 0, tzinfo=UTC),
        event_payload=(
            ("prev_sl", Price(value=Decimal("100.00"))),
            ("new_sl", Price(value=Decimal("95.00"))),
        ),
    )
    assert event.event_payload == (
        ("prev_sl", Price(value=Decimal("100.00"))),
        ("new_sl", Price(value=Decimal("95.00"))),
    )


# 23. Event immutability


def test_event_immutable(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.CANCELLED,
        timestamp_utc=datetime(2025, 6, 6, 0, 0, 0, tzinfo=UTC),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.event_type = EventType.REVISED  # type: ignore[misc]


# 24. Event does not embed recursive revision graph


def test_event_no_recursive_revision_graph(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.REVISED,
        timestamp_utc=datetime(2025, 7, 7, 0, 0, 0, tzinfo=UTC),
        previous_revision_id=uuid4(),
        new_revision_id=uuid4(),
    )
    # previous_revision_id and new_revision_id are UUID references, not embedded objects
    assert not isinstance(event.previous_revision_id, SignalRevision)
    assert not isinstance(event.new_revision_id, SignalRevision)


# 25. Provider independence


def test_event_provider_independent(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.SCALE_IN,
        timestamp_utc=datetime(2025, 8, 8, 0, 0, 0, tzinfo=UTC),
        provenance=ProviderSource(
            provider_name="provider_beta", signal_reference="ref-beta"
        ),
    )
    assert event.provenance.provider_name == "provider_beta"
    assert not hasattr(event, "telegram_message_id")


# 26. Broker independence


def test_event_broker_independent(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.EXECUTING,
        timestamp_utc=datetime(2025, 9, 9, 0, 0, 0, tzinfo=UTC),
    )
    assert not hasattr(event, "broker_reference")
    assert not hasattr(event, "order_id")
    assert not hasattr(event, "execution_result")


# 27. Naive datetime rejected


def test_event_naive_datetime_rejected(identity: SignalIdentity) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SignalEvent(
            event_id=uuid4(),
            signal_identity=identity,
            event_type=EventType.CANCELLED,
            timestamp_utc=datetime(2025, 1, 1, 0, 0, 0),  # noqa: DTZ001
        )


# 28. Malformed revision rejected


def test_invalid_revision_number_negative(identity: SignalIdentity) -> None:
    with pytest.raises(ValueError, match="positive int"):
        SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=-1,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="fp",
            created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        )


# 29. Invalid event payload mutable collections rejected


def test_event_payload_rejects_mutable_dict(identity: SignalIdentity) -> None:
    with pytest.raises(TypeError, match="unsupported"):
        SignalEvent(
            event_id=uuid4(),
            signal_identity=identity,
            event_type=EventType.REVISED,
            timestamp_utc=datetime(2025, 2, 2, 0, 0, 0, tzinfo=UTC),
            event_payload=(("bad", {"mutable": True}),),
        )


# 30. Invalid identifiers rejected


def test_invalid_event_id_type(identity: SignalIdentity) -> None:
    with pytest.raises(TypeError, match="event_id must be UUID"):
        SignalEvent(
            event_id="not-uuid",
            signal_identity=identity,
            event_type=EventType.CREATED,
            timestamp_utc=datetime(2025, 3, 3, 0, 0, 0, tzinfo=UTC),
        )


# 31. Fingerprint computed (empty input overwritten by derived value)


def test_fingerprint_computed_for_revision_empty_string(
    identity: SignalIdentity,
) -> None:
    snapshot = (("status", "CANCELLED"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="",
        created_at_utc=datetime(2025, 4, 4, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# 33. Fingerprint derivation: same snapshot → same fingerprint (A)


def test_fingerprint_derived_same_snapshot_same_fp(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"), ("direction", "BUY"))
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC),
    )
    assert rev1.fingerprint == rev2.fingerprint
    assert rev1.fingerprint == _canonical_fingerprint(snapshot)


# B. Different snapshot → different fingerprint


def test_fingerprint_derived_different_snapshot_different_fp(
    identity: SignalIdentity,
) -> None:
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("status", "COMPLETE"),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev_a.revision_id,
        canonical_snapshot=(("status", "CANCELLED"),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC),
    )
    assert rev_a.fingerprint != rev_b.fingerprint
    assert rev_a.fingerprint == _canonical_fingerprint((("status", "COMPLETE"),))
    assert rev_b.fingerprint == _canonical_fingerprint((("status", "CANCELLED"),))


# C. Changing revision_id → fingerprint unchanged


def test_fingerprint_unchanged_by_revision_id(identity: SignalIdentity) -> None:
    snapshot = (("entry_geometry", "SINGLE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=3,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2025, 2, 2, 0, 0, 0, tzinfo=UTC),
    )
    # fingerprint depends only on snapshot; changing revision_id would create a different revision
    # with the same fingerprint if snapshot unchanged
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# D. Changing logical_signal_id → fingerprint unchanged (same snapshot)


def test_fingerprint_unchanged_by_logical_signal_id() -> None:
    snapshot = (("status", "ACTIVE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=uuid4(),
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2025, 3, 3, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# E. Changing revision_number → fingerprint unchanged


def test_fingerprint_unchanged_by_revision_number(identity: SignalIdentity) -> None:
    snapshot = (("status", "ACTIVE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=10,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2025, 4, 4, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# F. Changing previous_revision_id → fingerprint unchanged


def test_fingerprint_unchanged_by_previous_revision_id(
    identity: SignalIdentity,
) -> None:
    snapshot = (("status", "DRAFT"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2025, 5, 5, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# G. Changing event_reference_id → fingerprint unchanged


def test_fingerprint_unchanged_by_event_reference_id(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=uuid4(),
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        event_reference_id=uuid4(),
        created_at_utc=datetime(2025, 6, 6, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# H. Changing created_at_utc → fingerprint unchanged


def test_fingerprint_unchanged_by_timestamp(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)


# I. Changing semantic snapshot field → fingerprint changes


def test_fingerprint_changes_with_semantic_content(identity: SignalIdentity) -> None:
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("status", "COMPLETE"),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 7, 7, 0, 0, 0, tzinfo=UTC),
    )
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev_a.revision_id,
        canonical_snapshot=(("status", "CANCELLED"),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 7, 7, 1, 0, 0, tzinfo=UTC),
    )
    assert rev_a.fingerprint != rev_b.fingerprint


# J. Reordering mapping keys → fingerprint unchanged (sorted normalization)


def test_fingerprint_unchanged_by_key_order(identity: SignalIdentity) -> None:
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("b", 2), ("a", 1)),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 8, 8, 0, 0, 0, tzinfo=UTC),
    )
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev_a.revision_id,
        canonical_snapshot=(("a", 1), ("b", 2)),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 8, 8, 1, 0, 0, tzinfo=UTC),
    )
    # Normalized fingerprint sorts keys, so order-independent
    assert rev_a.fingerprint == rev_b.fingerprint


# K. Changing tuple ordering (semantic) → fingerprint changes


def test_fingerprint_changes_by_tuple_order(identity: SignalIdentity) -> None:
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("levels", (1, 2)),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 9, 9, 0, 0, 0, tzinfo=UTC),
    )
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev_a.revision_id,
        canonical_snapshot=(("levels", (2, 1)),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 9, 9, 1, 0, 0, tzinfo=UTC),
    )
    assert rev_a.fingerprint != rev_b.fingerprint


# L. Decimal normalization: 10.5 == 10.500 → same fingerprint


def test_fingerprint_decimal_normalization(identity: SignalIdentity) -> None:
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(("price", Decimal("10.5")),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 10, 10, 0, 0, 0, tzinfo=UTC),
    )
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev_a.revision_id,
        canonical_snapshot=(("price", Decimal("10.500")),),
        fingerprint="ignored",
        created_at_utc=datetime(2025, 10, 10, 1, 0, 0, tzinfo=UTC),
    )
    assert rev_a.fingerprint == rev_b.fingerprint


# M. Unsupported snapshot value type rejected


def test_unsupported_snapshot_type_rejected(identity: SignalIdentity) -> None:
    with pytest.raises(TypeError, match="unsupported"):
        SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(("bad", {"dict": True}),),
            fingerprint="ignored",
            created_at_utc=datetime(2025, 11, 11, 0, 0, 0, tzinfo=UTC),
        )


# N. Fingerprint computed, not forged


def test_fingerprint_computed_not_forged(identity: SignalIdentity) -> None:
    snapshot = (("status", "COMPLETE"),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="wrong_value_should_be_overwritten",
        created_at_utc=datetime(2025, 12, 12, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == _canonical_fingerprint(snapshot)
    assert rev.fingerprint != "wrong_value_should_be_overwritten"


# 32. Mutable payload prevented at construction


def test_payload_immutable_tuple_only(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.CANCEL,
        signal_identity=identity,
        created_at_utc=datetime(2025, 5, 5, 0, 0, 0, tzinfo=UTC),
    )
    # Payload is frozen tuple; mutation attempt should fail
    with pytest.raises(dataclasses.FrozenInstanceError):
        instruction.payload += (("new", "item"),)  # type: ignore[operator]
