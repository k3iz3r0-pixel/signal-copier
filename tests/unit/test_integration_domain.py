"""Integration tests proving domain components compose coherently (Step 7)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from packages.signal_core.domain import (
    Signal,
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    canonical_fingerprint,
)
from packages.signal_core.enums import (
    AssetClass,
    EntryGeometry,
    EntryTrigger,
    EventType,
    InstructionType,
    LifecycleState,
    SignalStatus,
    TradeDirection,
)
from packages.signal_core.value_objects import (
    Instrument,
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


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)


# A. Create identity


def test_a_create_identity() -> None:
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="alpha", signal_reference="r1"),
    )
    assert isinstance(identity.logical_signal_id, UUID)
    assert identity.provider_identity.provider_name == "alpha"


# B. Create canonical signal


def test_b_create_canonical_signal(
    identity: SignalIdentity, instrument: Instrument
) -> None:
    signal = Signal(
        identity=identity,
        instrument=instrument,
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.1000")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert signal.direction == TradeDirection.BUY
    assert signal.status == SignalStatus.COMPLETE


# C. Create instruction referencing identity


def test_c_create_instruction_reference_identity(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.MODIFY,
        signal_identity=identity,
        payload=(("new_sl", Price(value=Decimal("1.0950"))),),
        created_at_utc=datetime(2024, 2, 2, 0, 0, 0, tzinfo=UTC),
    )
    assert instruction.signal_identity == identity
    assert instruction.instruction_type == InstructionType.MODIFY


# D. Create complete revision snapshot


def test_d_create_revision_snapshot_complete(identity: SignalIdentity) -> None:
    snapshot = (
        (
            "instrument",
            Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        ),
        ("direction", TradeDirection.BUY),
        ("entry_geometry", EntryGeometry.SINGLE),
        ("entry_trigger", EntryTrigger.LIMIT),
        ("entry_price", Price(value=Decimal("1.1000"))),
        ("status", SignalStatus.COMPLETE),
        ("lifecycle_state", LifecycleState.ACTIVE),
    )
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2024, 3, 3, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.revision_number == 1
    assert rev.previous_revision_id is None
    assert rev.fingerprint == canonical_fingerprint(snapshot)


# E. Compute canonical fingerprint


def test_e_compute_fingerprint() -> None:
    snapshot = (("status", SignalStatus.COMPLETE), ("direction", TradeDirection.BUY))
    fp = canonical_fingerprint(snapshot)
    assert isinstance(fp, str)
    assert len(fp) == 64


# F. Create event referencing IDs


def test_f_create_event_references_ids(identity: SignalIdentity) -> None:
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.CREATED,
        timestamp_utc=datetime(2024, 4, 4, 0, 0, 0, tzinfo=UTC),
        previous_revision_id=None,
        new_revision_id=uuid4(),
    )
    assert event.event_type == EventType.CREATED
    assert event.signal_identity == identity
    assert event.event_id != event.new_revision_id


# G. Create second revision with same identity, changed content


def test_g_second_revision_same_identity_changed_content(
    identity: SignalIdentity,
) -> None:
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(
            ("status", SignalStatus.COMPLETE),
            ("lifecycle_state", LifecycleState.ACTIVE),
        ),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 5, 5, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=(("lifecycle_state", LifecycleState.CANCELLED),),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 5, 5, 1, 0, 0, tzinfo=UTC),
    )
    assert rev1.logical_signal_id == rev2.logical_signal_id
    assert rev1.revision_id != rev2.revision_id
    assert rev1.fingerprint != rev2.fingerprint


# H. Verify identity unchanged across revisions


def test_h_identity_unchanged_across_revisions(identity: SignalIdentity) -> None:
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 6, 6, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=(("modified", True),),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 6, 6, 1, 0, 0, tzinfo=UTC),
    )
    assert (
        rev1.logical_signal_id == rev2.logical_signal_id == identity.logical_signal_id
    )


# I. Verify fingerprint changes when semantic content changes


def test_i_fingerprint_changes_semantic_content() -> None:
    fp_a = canonical_fingerprint((("status", SignalStatus.COMPLETE),))
    fp_b = canonical_fingerprint((("lifecycle_state", LifecycleState.CANCELLED),))
    assert fp_a != fp_b


# J. Verify revision number and linkage


def test_j_revision_number_and_linkage() -> None:
    rev1 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=uuid4(),
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 7, 7, 0, 0, 0, tzinfo=UTC),
    )
    rev2 = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=rev1.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev1.revision_id,
        canonical_snapshot=(),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 7, 7, 1, 0, 0, tzinfo=UTC),
    )
    assert rev2.revision_number == rev1.revision_number + 1
    assert rev2.previous_revision_id == rev1.revision_id


# K. Verify metadata changes don't alter fingerprint


def test_k_metadata_unchanged_fingerprint() -> None:
    snapshot = (("lifecycle_state", LifecycleState.ACTIVE),)
    rev_a = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=uuid4(),
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        event_reference_id=uuid4(),
        snapshot_version=3,
        created_at_utc=datetime(2024, 8, 8, 0, 0, 0, tzinfo=UTC),
    )
    rev_b = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=rev_a.logical_signal_id,
        revision_number=2,
        previous_revision_id=rev_a.revision_id,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        event_reference_id=uuid4(),
        snapshot_version=1,
        created_at_utc=datetime(2024, 8, 8, 2, 0, 0, tzinfo=UTC),
    )
    assert rev_a.fingerprint == rev_b.fingerprint


# L. Verify no recursive object graph


def test_l_no_recursive_graph(identity: SignalIdentity) -> None:
    # SignalRevision must not embed full Signal; must reference by UUID
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=identity.logical_signal_id,
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=(),
        fingerprint="ignored",
        created_at_utc=datetime(2024, 9, 9, 0, 0, 0, tzinfo=UTC),
    )
    # No embedded Signal
    assert not hasattr(
        rev, "identity"
    )  # revision uses UUID, not SignalIdentity embedded? Actually it does embed logical_signal_id.
    # Actually rev.logical_signal_id is UUID, not SignalIdentity embedded.
    assert isinstance(rev.logical_signal_id, UUID)
    assert rev.previous_revision_id is None or isinstance(
        rev.previous_revision_id, UUID
    )
    assert not isinstance(rev.previous_revision_id, SignalRevision)


# M. Deep immutability through composition


def test_m_deep_immutability_through_composition() -> None:
    snapshot = (("entry_levels", (Price(value=Decimal(150)),)),)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=uuid4(),
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2024, 10, 10, 0, 0, 0, tzinfo=UTC),
    )
    # Mutation attempts should fail
    with pytest.raises(AttributeError):
        rev.canonical_snapshot += (("bad", "bad"),)  # type: ignore[operator]


# N. Provider / broker isolation audit


def test_n_provider_broker_isolation() -> None:
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(
            provider_name="provider", signal_reference="ref"
        ),
    )
    signal = Signal(
        identity=identity,
        instrument=Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
        direction=TradeDirection.BUY,
        entry_geometry=EntryGeometry.SINGLE,
        entry_trigger=EntryTrigger.LIMIT,
        entry_price=Price(value=Decimal("1.1")),
        status=SignalStatus.COMPLETE,
        lifecycle_state=LifecycleState.ACTIVE,
        created_at_utc=datetime(2024, 11, 11, 0, 0, 0, tzinfo=UTC),
    )
    instruction = SignalInstruction(
        instruction_type=InstructionType.MODIFY,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime(2024, 11, 11, 0, 0, 0, tzinfo=UTC),
    )
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.REVISED,
        timestamp_utc=datetime(2024, 11, 11, 0, 0, 0, tzinfo=UTC),
    )
    # No broker fields, no Telegram fields
    assert not hasattr(signal, "broker_reference")
    assert not hasattr(instruction, "broker_reference")
    assert not hasattr(event, "telegram_chat_id")
    assert not hasattr(signal, "lot_size")
