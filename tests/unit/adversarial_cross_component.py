"""Adversarial Category 13 — Cross-component combination attacks."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from packages.signal_core.domain import (
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    canonical_fingerprint,
)
from packages.signal_core.enums import (
    AssetClass,
    EventType,
    InstructionType,
    SignalStatus,
)
from packages.signal_core.value_objects import (
    Instrument,
    ProviderSource,
)


def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="test", signal_reference="t"),
    )


def instrument() -> Instrument:
    return Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)


class TestCrossComponentIdentityConsistency:
    def test_identity_unchanged_across_revision_and_event(self) -> None:
        logical = uuid4()
        id_ref = SignalIdentity(
            logical_signal_id=logical,
            provider_identity=ProviderSource(provider_name="p", signal_reference="r"),
        )
        snapshot = (("status", SignalStatus.ACTIVE),)
        rev = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=logical,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        event = SignalEvent(
            event_id=uuid4(),
            signal_identity=id_ref,
            event_type=EventType.REVISED,
            timestamp_utc=datetime(2024, 1, 2, tzinfo=UTC),
            previous_revision_id=rev.revision_id,
            new_revision_id=uuid4(),
        )
        instruction = SignalInstruction(
            instruction_type=InstructionType.MODIFY,
            signal_identity=id_ref,
            created_at_utc=datetime(2024, 1, 2, tzinfo=UTC),
        )
        assert (
            rev.logical_signal_id
            == event.signal_identity.logical_signal_id
            == instruction.signal_identity.logical_signal_id
            == logical
        )

    def test_fingerprint_independent_of_revision_metadata_across_event_and_instruction(
        self,
    ) -> None:
        snapshot = (("status", SignalStatus.COMPLETE),)
        fp = canonical_fingerprint(snapshot)
        rev = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=5,
            previous_revision_id=uuid4(),
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            event_reference_id=uuid4(),
            snapshot_version=7,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert rev.fingerprint == fp
        # Instruction carries identity only; fingerprint is a revision-level concept.
        # No leakage between identity/reference and fingerprint content.


class TestCrossComponentInconsistencyAttack:
    def test_revision_snapshot_with_mutable_dict_fails_at_revision_level(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            SignalRevision(
                revision_id=uuid4(),
                logical_signal_id=uuid4(),
                revision_number=1,
                previous_revision_id=None,
                canonical_snapshot=(("bad", {"nested": True}),),
                fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_event_payload_dict_fails_at_event_level(self) -> None:
        id_ref = identity()
        with pytest.raises(TypeError, match="unsupported"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=id_ref,
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                event_payload=(("bad", {"nested": True}),),
            )

    def test_instruction_payload_dict_fails_at_instruction_level(self) -> None:
        id_ref = identity()
        with pytest.raises(TypeError, match="unsupported"):
            SignalInstruction(
                instruction_type=InstructionType.MODIFY,
                signal_identity=id_ref,
                payload=(("bad", {"nested": True}),),
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_all_three_components_reject_same_bad_value(self) -> None:
        bad_snapshot = (("bad", [1, 2, 3]),)
        # Revision
        with pytest.raises(TypeError, match="unsupported"):
            SignalRevision(
                revision_id=uuid4(),
                logical_signal_id=uuid4(),
                revision_number=1,
                previous_revision_id=None,
                canonical_snapshot=bad_snapshot,
                fingerprint="ignored",
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )
        # Event payload
        id_ref = identity()
        with pytest.raises(TypeError, match="unsupported"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=id_ref,
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                event_payload=bad_snapshot,
            )
        # Instruction payload
        with pytest.raises(TypeError, match="unsupported"):
            SignalInstruction(
                instruction_type=InstructionType.MODIFY,
                signal_identity=id_ref,
                payload=bad_snapshot,
                created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )


class TestCrossComponentIdentityReferenceSeparation:
    def test_event_references_identity_not_embedded_signal(self) -> None:
        id_ref = identity()
        event = SignalEvent(
            event_id=uuid4(),
            signal_identity=id_ref,
            event_type=EventType.CREATED,
            timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert event.signal_identity == id_ref
        assert not hasattr(event, "instrument")
        assert not hasattr(event, "entry_price")

    def test_revision_references_identity_by_uuid_not_embedded_object(self) -> None:
        logical = uuid4()
        rev = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=logical,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert isinstance(rev.logical_signal_id, UUID)
        assert not isinstance(rev.logical_signal_id, SignalIdentity)

    def test_instruction_references_identity_by_reference_not_full_signal(self) -> None:
        id_ref = identity()
        instruction = SignalInstruction(
            instruction_type=InstructionType.CANCEL,
            signal_identity=id_ref,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert isinstance(instruction.signal_identity, SignalIdentity)
        assert instruction.signal_identity == id_ref
        assert not hasattr(instruction, "instrument")
