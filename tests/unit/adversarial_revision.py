"""Adversarial Category 7 — Revision attacks."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from packages.signal_core.domain import SignalRevision, canonical_fingerprint
from packages.signal_core.enums import LifecycleState, SignalStatus
from packages.signal_core.value_objects import Price


class TestRevisionSequenceAdversarial:
    def test_first_revision_requires_none_previous(self) -> None:
        with pytest.raises(ValueError, match="First revision"):
            SignalRevision(
                revision_id=uuid4(), logical_signal_id=uuid4(),
                revision_number=1, previous_revision_id=uuid4(),
                canonical_snapshot=(), fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_revision_number_zero_fails(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            SignalRevision(
                revision_id=uuid4(), logical_signal_id=uuid4(),
                revision_number=0, previous_revision_id=None,
                canonical_snapshot=(), fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_negative_revision_number_fails(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            SignalRevision(
                revision_id=uuid4(), logical_signal_id=uuid4(),
                revision_number=-5, previous_revision_id=None,
                canonical_snapshot=(), fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_second_revision_requires_previous(self) -> None:
        with pytest.raises(ValueError, match="requires"):
            SignalRevision(
                revision_id=uuid4(), logical_signal_id=uuid4(),
                revision_number=2, previous_revision_id=None,
                canonical_snapshot=(), fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_large_revision_number_accepted(self) -> None:
        rev = SignalRevision(
            revision_id=uuid4(), logical_signal_id=uuid4(),
            revision_number=9999, previous_revision_id=uuid4(),
            canonical_snapshot=(), fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert rev.revision_number == 9999

    def test_same_snapshot_different_revision_fingerprint_equal(self) -> None:
        snapshot = (("status", SignalStatus.ACTIVE),)
        rev_a = SignalRevision(
            revision_id=uuid4(), logical_signal_id=uuid4(),
            revision_number=1, previous_revision_id=None,
            canonical_snapshot=snapshot, fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(), logical_signal_id=rev_a.logical_signal_id,
            revision_number=2, previous_revision_id=rev_a.revision_id,
            canonical_snapshot=snapshot, fingerprint="ignored",
            created_at_utc=datetime(2024, 2, 2, tzinfo=UTC),
        )
        assert rev_a.fingerprint == rev_b.fingerprint
        assert rev_a.revision_id != rev_b.revision_id

    def test_changed_snapshot_fingerprint_changes(self) -> None:
        rev_a = SignalRevision(
            revision_id=uuid4(), logical_signal_id=uuid4(),
            revision_number=1, previous_revision_id=None,
            canonical_snapshot=(("a", 1),), fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(), logical_signal_id=rev_a.logical_signal_id,
            revision_number=2, previous_revision_id=rev_a.revision_id,
            canonical_snapshot=(("a", 2),), fingerprint="ignored",
            created_at_utc=datetime(2024, 2, 2, tzinfo=UTC),
        )
        assert rev_a.fingerprint != rev_b.fingerprint

    def test_empty_snapshot_fingerprint_deterministic(self) -> None:
        snapshot = ()
        fp1 = canonical_fingerprint(snapshot)
        fp2 = canonical_fingerprint(snapshot)
        assert fp1 == fp2
        assert isinstance(fp1, str)
        assert len(fp1) == 64

    def test_revision_id_independence_invariant(self) -> None:
        same_uuid = uuid4()
        with pytest.raises(ValueError, match="independence"):
            SignalRevision(
                revision_id=same_uuid, logical_signal_id=same_uuid,
                revision_number=1, previous_revision_id=None,
                canonical_snapshot=(), fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_snapshot_not_tuple_fails(self) -> None:
        with pytest.raises(TypeError, match="frozen tuple"):
            SignalRevision(
                revision_id=uuid4(), logical_signal_id=uuid4(),
                revision_number=1, previous_revision_id=None,
                canonical_snapshot={"bad": True}, fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )
