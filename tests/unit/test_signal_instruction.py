import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import SignalIdentity, SignalInstruction
from packages.signal_core.enums import InstructionType, TradeDirection
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


# 1. OPEN


def test_open_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.OPEN,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.OPEN
    assert instruction.signal_identity == identity


# 2. MODIFY


def test_modify_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.MODIFY,
        signal_identity=identity,
        payload=(("field", "value"),),
        created_at_utc=datetime(2024, 2, 2, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.MODIFY
    assert instruction.payload == (("field", "value"),)


# 3. CANCEL


def test_cancel_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.CANCEL,
        signal_identity=identity,
        created_at_utc=datetime(2024, 3, 3, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.CANCEL
    assert instruction.payload == ()


# 4. CLOSE


def test_close_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.CLOSE,
        signal_identity=identity,
        created_at_utc=datetime(2024, 4, 4, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.CLOSE


# 5. PARTIAL_CLOSE


def test_partial_close_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.PARTIAL_CLOSE,
        signal_identity=identity,
        payload=(("quantity_ref", "partial_50_percent"),),
        created_at_utc=datetime(2024, 5, 5, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.PARTIAL_CLOSE


# 6. MOVE_SL


def test_move_sl_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.MOVE_SL,
        signal_identity=identity,
        payload=(("new_sl", Price(value=Decimal("145.00"))),),
        created_at_utc=datetime(2024, 6, 6, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.MOVE_SL
    # Payload references Price, not broker order
    assert isinstance(instruction.payload, tuple)


# 7. MOVE_TP


def test_move_tp_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.MOVE_TP,
        signal_identity=identity,
        payload=(
            (
                "new_tp",
                (Price(value=Decimal("160.00")), Price(value=Decimal("170.00"))),
            ),
        ),
        created_at_utc=datetime(2024, 7, 7, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.MOVE_TP


# 8. BREAKEVEN


def test_breakeven_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.BREAKEVEN,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime(2024, 8, 8, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.BREAKEVEN


# 9. TRAIL


def test_trail_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.TRAIL,
        signal_identity=identity,
        payload=(("trail_distance", Decimal("5.0")),),
        created_at_utc=datetime(2024, 9, 9, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.TRAIL


# 10. SCALE_IN


def test_scale_in_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.SCALE_IN,
        signal_identity=identity,
        payload=(("new_levels", (Price(value=Decimal("146.00")),)),),
        created_at_utc=datetime(2024, 10, 10, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.SCALE_IN


# 11. SCALE_OUT


def test_scale_out_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.SCALE_OUT,
        signal_identity=identity,
        payload=(("scale_ref", "reduce_50_percent"),),
        created_at_utc=datetime(2024, 11, 11, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.SCALE_OUT


# 12. REVERSE


def test_reverse_instruction(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.REVERSE,
        signal_identity=identity,
        payload=(("new_direction", TradeDirection.SELL),),
        created_at_utc=datetime(2024, 12, 12, 12, 0, 0, tzinfo=UTC),
    )
    assert instruction.instruction_type == InstructionType.REVERSE


# Required fields


def test_instruction_requires_type_and_identity(identity: SignalIdentity) -> None:
    with pytest.raises(TypeError):
        SignalInstruction(
            instruction_type="OPEN",  # invalid type
            signal_identity=identity,
            created_at_utc=datetime.now(UTC),
        )
    with pytest.raises(TypeError):
        SignalInstruction(
            instruction_type=InstructionType.CANCEL,
            signal_identity="not_identity",  # invalid identity
            created_at_utc=datetime.now(UTC),
        )


# Deep immutability


def test_instruction_immutable(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.CANCEL,
        signal_identity=identity,
        created_at_utc=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        instruction.instruction_type = InstructionType.MODIFY  # type: ignore[misc]


# Semantic distinction: not a broker order


def test_instruction_is_not_broker_order(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.MOVE_SL,
        signal_identity=identity,
        payload=(("new_sl_price", Price(value=Decimal("145.00"))),),
        created_at_utc=datetime(2024, 5, 5, 12, 0, 0, tzinfo=UTC),
    )
    # Must reference identity, not embed full Signal; must not have broker fields
    assert isinstance(instruction.signal_identity, SignalIdentity)
    assert not hasattr(instruction, "broker_reference")
    assert not hasattr(instruction, "order_id")
    assert not hasattr(instruction, "lot_size")
    assert instruction.instruction_type.name == "MOVE_SL"


# Provider syntax examples preserved canonically


def test_move_sl_to_be_preserved(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.BREAKEVEN,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime.now(UTC),
    )
    assert instruction.instruction_type == InstructionType.BREAKEVEN


def test_partial_close_50_percent_preserved(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.PARTIAL_CLOSE,
        signal_identity=identity,
        payload=(("quantity_ref", "close_50_percent"),),
        created_at_utc=datetime.now(UTC),
    )
    assert instruction.instruction_type == InstructionType.PARTIAL_CLOSE
    assert instruction.payload == (("quantity_ref", "close_50_percent"),)


def test_cancel_pending_signal_preserved(identity: SignalIdentity) -> None:
    instruction = SignalInstruction(
        instruction_type=InstructionType.CANCEL,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime.now(UTC),
    )
    assert instruction.instruction_type == InstructionType.CANCEL


# Invalid payload mutation prevented


def test_payload_immutable_and_rejects_mutable_collections(
    identity: SignalIdentity,
) -> None:
    with pytest.raises(TypeError, match="unsupported"):
        SignalInstruction(
            instruction_type=InstructionType.OPEN,
            signal_identity=identity,
            payload=(("bad", ["list_not_tuple"]),),
            created_at_utc=datetime.now(UTC),
        )
    with pytest.raises(TypeError, match="unsupported"):
        SignalInstruction(
            instruction_type=InstructionType.OPEN,
            signal_identity=identity,
            payload=(("bad", {"dict_not_tuple"}),),
            created_at_utc=datetime.now(UTC),
        )


# Invalid created_at_utc (naive / non-UTC)


def test_invalid_naive_datetime_rejected(identity: SignalIdentity) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SignalInstruction(
            instruction_type=InstructionType.CANCEL,
            signal_identity=identity,
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0),  # noqa: DTZ001 — intentional naive datetime for rejection test
        )


def test_invalid_non_utc_datetime_rejected(identity: SignalIdentity) -> None:
    import datetime

    with pytest.raises(ValueError, match="UTC"):
        SignalInstruction(
            instruction_type=InstructionType.CANCEL,
            signal_identity=identity,
            created_at_utc=datetime.datetime(
                2024,
                1,
                1,
                0,
                0,
                0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=5)),
            ),
        )


# Hashing / equality


def test_instruction_equality_and_hash(identity: SignalIdentity) -> None:
    i1 = SignalInstruction(
        instruction_type=InstructionType.REVERSE,
        signal_identity=identity,
        payload=(("new_direction", TradeDirection.SELL),),
        created_at_utc=datetime(2024, 3, 3, 12, 0, 0, tzinfo=UTC),
    )
    i2 = SignalInstruction(
        instruction_type=InstructionType.REVERSE,
        signal_identity=identity,
        payload=(("new_direction", TradeDirection.SELL),),
        created_at_utc=datetime(2024, 3, 3, 12, 0, 0, tzinfo=UTC),
    )
    assert i1 == i2
    assert hash(i1) == hash(i2)


# Deterministic construction


def test_deterministic_construction(identity: SignalIdentity) -> None:
    i1 = SignalInstruction(
        instruction_type=InstructionType.OPEN,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    i2 = SignalInstruction(
        instruction_type=InstructionType.OPEN,
        signal_identity=identity,
        payload=(),
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert i1 == i2
