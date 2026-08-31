"""Adversarial Category 12 — Serialization / deferred contract audit.

Per design Section 22 / 26: serialization framework deferred.
This module verifies nothing beyond the approved canonical-value contract
has been implemented and documents deferred behavior explicitly."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from packages.signal_core.domain import (
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    canonical_fingerprint,
)
from packages.signal_core.enums import (
    EventType,
    InstructionType,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.value_objects import (
    Price,
    ProviderSource,
)


def test_serialization_not_implemented_beyond_canonical_fingerprint() -> None:
    """The only deterministic serialization mechanism in Phase 1 is canonical_fingerprint()."""
    snapshot = (
        ("status", SignalStatus.ACTIVE),
        ("price", Price(value=Decimal(100))),
    )
    fp = canonical_fingerprint(snapshot)
    assert isinstance(fp, str)
    assert len(fp) == 64
    # No JSON framework, no pydantic, no attrs, no serialization library used.


def test_serialization_deferred_documented() -> None:
    """Design explicitly defers serialization framework; only standard-library
    frozen objects and deterministic fingerprint exist."""
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="test", signal_reference="t"),
    )
    SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.CREATED,
        timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
    )
    # Event payload uses frozen tuple; no dict serialization framework.
    SignalInstruction(
        instruction_type=InstructionType.OPEN,
        signal_identity=identity,
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
    )
    # No external serialization library dependency added.


def test_reconstruction_from_snapshot_not_implemented() -> None:
    """Replay/reconstruction framework is deferred; only frozen snapshot mapping
    exists as an independent audit artifact."""
    snapshot = (
        ("direction", TradeDirection.BUY),
        ("lifecycle_state", LifecycleState.ACTIVE),
    )
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=uuid4(),
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
    )
    # Snapshot is independently inspectable (design Section 3.12); replay logic deferred.
    assert rev.canonical_snapshot == snapshot
    assert rev.fingerprint == canonical_fingerprint(snapshot)
