"""Adversarial Category 9 — Event attacks."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from packages.signal_core.domain import SignalEvent, SignalIdentity
from packages.signal_core.enums import EventType
from packages.signal_core.value_objects import Price, ProviderSource


def identity() -> SignalIdentity:
    return SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="test", signal_reference="t"),
    )


class TestEventAdversarial:
    def test_invalid_event_id_string(self) -> None:
        with pytest.raises(TypeError, match="event_id"):
            SignalEvent(
                event_id="not_uuid",
                signal_identity=identity(),
                event_type=EventType.CREATED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_invalid_signal_identity_string(self) -> None:
        with pytest.raises(TypeError, match="signal_identity"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity="not_identity",
                event_type=EventType.CREATED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_invalid_event_type_string(self) -> None:
        with pytest.raises(TypeError):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type="CREATED",
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.CREATED,
                timestamp_utc=datetime(2024, 1, 1, 0, 0, 0),  # noqa: DTZ001
            )

    def test_non_utc_timestamp_rejected(self) -> None:
        import datetime

        with pytest.raises(ValueError, match="UTC"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.CREATED,
                timestamp_utc=datetime(
                    2024,
                    1,
                    1,
                    0,
                    0,
                    0,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=3)),
                ),
            )

    def test_previous_revision_id_not_uuid_string(self) -> None:
        with pytest.raises(TypeError, match="previous_revision_id"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                previous_revision_id="bad",
            )

    def test_new_revision_id_not_uuid_string(self) -> None:
        with pytest.raises(TypeError, match="new_revision_id"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                new_revision_id="bad",
            )

    def test_mutable_dict_payload_rejected(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                event_payload=(("bad", {"nested": True}),),
            )

    def test_mutable_list_payload_rejected(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                event_payload=(("bad", [1, 2, 3]),),
            )

    def test_nested_tuple_with_dict_payload_rejected(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                event_payload=(("nested", (("inner", {"bad": True}),)),),
            )

    def test_provenance_wrong_type_string(self) -> None:
        with pytest.raises(TypeError, match="provenance"):
            SignalEvent(
                event_id=uuid4(),
                signal_identity=identity(),
                event_type=EventType.REVISED,
                timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
                provenance="provider",
            )

    def test_event_payload_immutable_tuple_only(self) -> None:
        event = SignalEvent(
            event_id=uuid4(),
            signal_identity=identity(),
            event_type=EventType.SL_MOVED,
            timestamp_utc=datetime(2024, 5, 5, 0, 0, 0, tzinfo=UTC),
            event_payload=(
                ("prev_sl", Price(value=Decimal("100.00"))),
                ("new_sl", Price(value=Decimal("95.00"))),
            ),
        )
        assert event.event_payload[0][0] == "prev_sl"

    def test_event_is_historical_not_revision(self) -> None:
        # Event references identity, not embedded Signal; references revisions by UUID.
        event = SignalEvent(
            event_id=uuid4(),
            signal_identity=identity(),
            event_type=EventType.REVISED,
            timestamp_utc=datetime(2024, 1, 1, tzinfo=UTC),
            previous_revision_id=uuid4(),
            new_revision_id=uuid4(),
        )
        assert isinstance(event.previous_revision_id, UUID)
        assert isinstance(event.new_revision_id, UUID)
        assert not hasattr(event, "revision_id")
