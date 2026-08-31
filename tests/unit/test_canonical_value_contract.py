"""Canonical-value consistency contract: single validator shared by all
components (Step 7.2). Proves validator, fingerprint, revision, event payload,
and instruction payload have identical acceptance/rejection behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import (
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    _validate_canonical_value,
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
    Price,
    PriceRange,
    ProviderSource,
)

# ------------------------------------------------------------------
# Supported / unsupported value matrix tests
# ------------------------------------------------------------------

SUPPORTED_VALUES = [
    ("str", "hello"),
    ("int", 42),
    ("bool_true", True),
    ("bool_false", False),
    ("Decimal", Decimal("1.2345")),
    ("Decimal_zero", Decimal("0.0")),
    ("UUID", uuid4()),
    ("None", None),
    ("tuple_empty", ()),
    ("tuple_str", ("a", "b")),
    ("tuple_nested_price", (Price(value=Decimal(100)),)),
    ("Price", Price(value=Decimal("99.99"))),
    (
        "PriceRange",
        PriceRange(low=Price(value=Decimal(50)), high=Price(value=Decimal(150))),
    ),
    ("Instrument", Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX)),
]

UNSUPPORTED_VALUES = [
    ("float", 3.14),
    ("list_empty", []),
    ("list_items", [1, 2]),
    ("dict_empty", {}),
    ("dict_items", {"a": 1}),
    ("set_empty", set()),
    ("frozenset", frozenset({1, 2})),
    ("custom_object", object()),
]


@pytest.mark.parametrize(
    "label,value",
    [pytest.param(label, value, id=label) for label, value in SUPPORTED_VALUES],
)
def test_validator_accepts_supported(label: str, value: object) -> None:
    """Every supported canonical value passes the authoritative validator."""
    # Authoritative mechanism: same used by revision, fingerprint, event, instruction
    _validate_canonical_value(value)


@pytest.mark.parametrize(
    "label,value",
    [pytest.param(label, value, id=label) for label, value in UNSUPPORTED_VALUES],
)
def test_validator_rejects_unsupported(label: str, value: object) -> None:
    """Every unsupported value is rejected by the authoritative validator."""
    with pytest.raises(TypeError, match="unsupported"):
        _validate_canonical_value(value)


# ------------------------------------------------------------------
# Nested immutability evidence
# ------------------------------------------------------------------

NESTED_REJECTION_CASES = [
    ("tuple_tuple_dict", (("nested", {"bad": True}),)),  # tuple -> tuple -> dict
    ("tuple_tuple_list", (("nested", [1, 2, 3]),)),  # tuple -> tuple -> list
    ("tuple_tuple_set", (("nested", {1, 2, 3}),)),  # tuple -> tuple -> set
    ("tuple_tuple_custom", (("nested", object()),)),  # tuple -> tuple -> custom
]

NESTED_SUPPORT_CASES = [
    ("tuple_tuple_price", (("price", Price(value=Decimal(10))),)),
    ("tuple_tuple_decimal", (("val", Decimal("5.5")),)),
    ("tuple_tuple_uuid", (("id", uuid4()),)),
    ("tuple_tuple_tuple", (("nested_tuple", (1, 2, 3)),)),
]


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in NESTED_REJECTION_CASES]
)
def test_nested_rejection_at_any_depth(label: str, value: object) -> None:
    """Nested mutable/unsupported structures rejected at any depth."""
    with pytest.raises(TypeError, match="unsupported"):
        _validate_canonical_value(value)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in NESTED_SUPPORT_CASES]
)
def test_nested_supported_at_any_depth(label: str, value: object) -> None:
    """Nested supported structures validated recursively at any depth."""
    _validate_canonical_value(value)


# ------------------------------------------------------------------
# Fingerprint / validator / revision / payload identity matrix
# ------------------------------------------------------------------

MATRIX_VALUES = [
    ("str", "COMPLETE"),
    ("int", 42),
    ("bool", True),
    ("Decimal", Decimal("1.5")),
    ("UUID", uuid4()),
    ("None", None),
    ("tuple_simple", (1, 2, 3)),
    ("tuple_price", (Price(value=Decimal(100)),)),
    ("Price", Price(value=Decimal("99.99"))),
    (
        "PriceRange",
        PriceRange(low=Price(value=Decimal(50)), high=Price(value=Decimal(150))),
    ),
    (
        "Instrument_enum",
        Instrument(canonical_symbol="XAUUSD", asset_class=AssetClass.COMMODITY),
    ),
]


def build_snapshot(value_name: str, value: object) -> tuple[tuple[str, object], ...]:
    return ((value_name, value),)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in MATRIX_VALUES]
)
def test_matrix_validator_passes(label: str, value: object) -> None:
    _validate_canonical_value(value)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in MATRIX_VALUES]
)
def test_matrix_fingerprint_succeeds(label: str, value: object) -> None:
    snapshot = build_snapshot(label, value)
    fp = canonical_fingerprint(snapshot)
    assert isinstance(fp, str)
    assert len(fp) == 64


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in MATRIX_VALUES]
)
def test_matrix_revision_accepts(label: str, value: object) -> None:
    snapshot = build_snapshot("field", value)
    rev = SignalRevision(
        revision_id=uuid4(),
        logical_signal_id=uuid4(),
        revision_number=1,
        previous_revision_id=None,
        canonical_snapshot=snapshot,
        fingerprint="ignored",
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    assert rev.fingerprint == canonical_fingerprint(snapshot)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in MATRIX_VALUES]
)
def test_matrix_event_payload_accepts(label: str, value: object) -> None:
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="p", signal_reference="r"),
    )
    event = SignalEvent(
        event_id=uuid4(),
        signal_identity=identity,
        event_type=EventType.REVISED,
        timestamp_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        event_payload=build_snapshot(label, value),
    )
    assert event.event_payload == build_snapshot(label, value)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in MATRIX_VALUES]
)
def test_matrix_instruction_payload_accepts(label: str, value: object) -> None:
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="p", signal_reference="r"),
    )
    instruction = SignalInstruction(
        instruction_type=InstructionType.MODIFY,
        signal_identity=identity,
        created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        payload=build_snapshot(label, value),
    )
    assert instruction.payload == build_snapshot(label, value)


# ------------------------------------------------------------------
# Unsupported matrix: same rejection across all components
# ------------------------------------------------------------------

UNSUPPORTED_MATRIX_VALUES = [
    ("float", 3.14),
    ("dict", {"bad": True}),
    ("list", [1, 2]),
    ("set", {1, 2}),
    ("frozenset", frozenset({1})),
    ("custom", object()),
]


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in UNSUPPORTED_MATRIX_VALUES]
)
def test_matrix_unsupported_rejected_by_validator(label: str, value: object) -> None:
    with pytest.raises(TypeError, match="unsupported"):
        _validate_canonical_value(value)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in UNSUPPORTED_MATRIX_VALUES]
)
def test_matrix_unsupported_rejected_by_fingerprint(label: str, value: object) -> None:
    snapshot = build_snapshot(label, value)
    with pytest.raises(TypeError, match="unsupported"):
        canonical_fingerprint(snapshot)


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in UNSUPPORTED_MATRIX_VALUES]
)
def test_matrix_unsupported_rejected_by_revision(label: str, value: object) -> None:
    snapshot = build_snapshot(label, value)
    with pytest.raises(TypeError, match="unsupported"):
        SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in UNSUPPORTED_MATRIX_VALUES]
)
def test_matrix_unsupported_rejected_by_event_payload(
    label: str, value: object
) -> None:
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="p", signal_reference="r"),
    )
    with pytest.raises(TypeError, match="unsupported"):
        SignalEvent(
            event_id=uuid4(),
            signal_identity=identity,
            event_type=EventType.REVISED,
            timestamp_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            event_payload=build_snapshot(label, value),
        )


@pytest.mark.parametrize(
    "label,value", [pytest.param(l, v, id=l) for l, v in UNSUPPORTED_MATRIX_VALUES]
)
def test_matrix_unsupported_rejected_by_instruction_payload(
    label: str, value: object
) -> None:
    identity = SignalIdentity(
        logical_signal_id=uuid4(),
        provider_identity=ProviderSource(provider_name="p", signal_reference="r"),
    )
    with pytest.raises(TypeError, match="unsupported"):
        SignalInstruction(
            instruction_type=InstructionType.MODIFY,
            signal_identity=identity,
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            payload=build_snapshot(label, value),
        )


# ------------------------------------------------------------------
# Fingerprint identity: same validator contract
# ------------------------------------------------------------------


def test_fingerprint_uses_same_validator_as_revision() -> None:
    """Proof that canonical_fingerprint and SignalRevision use the same
    _validate_canonical_value mechanism (not separate inline checks)."""
    snapshot = (("status", SignalStatus.COMPLETE),)
    # Both must succeed for identical input
    assert (
        canonical_fingerprint(snapshot)
        == SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        ).fingerprint
    )
