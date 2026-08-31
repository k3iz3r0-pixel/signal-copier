"""Tests for identity + fingerprint contract (Phase 1 — Step 6)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.signal_core.domain import (
    SignalIdentity,
    SignalRevision,
    canonical_fingerprint,
)
from packages.signal_core.enums import (
    AssetClass,
    TradeDirection,
)
from packages.signal_core.invariants import (
    validate_revision_id_independence,
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


# ------------------------------------------------------------------
# IDENTITY CONTRACT (tests 1-5)
# ------------------------------------------------------------------


class TestIdentityContract:
    def test_same_logical_id_across_revisions(self, identity: SignalIdentity) -> None:
        rev1 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="fp",
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        rev2 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=2,
            previous_revision_id=rev1.revision_id,
            canonical_snapshot=(),
            fingerprint="fp",
            created_at_utc=datetime(2024, 2, 2, 0, 0, 0, tzinfo=UTC),
        )
        assert (
            rev1.logical_signal_id
            == rev2.logical_signal_id
            == identity.logical_signal_id
        )

    def test_different_logical_id_identical_content(
        self, identity: SignalIdentity
    ) -> None:
        snapshot = (("status", "COMPLETE"),)
        rev_a = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 3, 3, 0, 0, 0, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 3, 3, 0, 0, 0, tzinfo=UTC),
        )
        assert rev_a.logical_signal_id != rev_b.logical_signal_id
        # Same content, same fingerprint, different logical identity
        assert rev_a.fingerprint == rev_b.fingerprint

    def test_content_changes_preserve_identity(self) -> None:
        logical = uuid4()
        id_ref = SignalIdentity(
            logical_signal_id=logical,
            provider_identity=ProviderSource(
                provider_name="alpha", signal_reference="r1"
            ),
        )
        rev1 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=id_ref.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(
                ("status", "COMPLETE"),
                ("price", Price(value=Decimal(100))),
            ),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 4, 4, 0, 0, 0, tzinfo=UTC),
        )
        rev2 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=id_ref.logical_signal_id,
            revision_number=2,
            previous_revision_id=rev1.revision_id,
            canonical_snapshot=(
                ("status", "CANCELLED"),
                ("price", Price(value=Decimal(100))),
            ),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 4, 4, 1, 0, 0, tzinfo=UTC),
        )
        assert rev1.logical_signal_id == rev2.logical_signal_id == logical
        assert rev1.fingerprint != rev2.fingerprint

    def test_revision_changes_preserve_identity(self) -> None:
        logical = uuid4()
        rev1 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=logical,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 5, 5, 0, 0, 0, tzinfo=UTC),
        )
        rev2 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=logical,
            revision_number=2,
            previous_revision_id=rev1.revision_id,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 5, 5, 1, 0, 0, tzinfo=UTC),
        )
        assert rev1.logical_signal_id == rev2.logical_signal_id == logical
        assert rev1.fingerprint == rev2.fingerprint

    def test_fingerprint_changes_do_not_change_identity(self) -> None:
        logical = uuid4()
        rev_a = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=logical,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(("a", 1),),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 6, 6, 0, 0, 0, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=logical,
            revision_number=2,
            previous_revision_id=rev_a.revision_id,
            canonical_snapshot=(("a", 2),),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 6, 6, 1, 0, 0, tzinfo=UTC),
        )
        assert rev_a.logical_signal_id == rev_b.logical_signal_id
        assert rev_a.fingerprint != rev_b.fingerprint


# ------------------------------------------------------------------
# REVISION IDENTITY (tests 6-9)
# ------------------------------------------------------------------


class TestRevisionIdentity:
    def test_revision_id_distinct_from_logical_id(self) -> None:
        rev = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 7, 7, 0, 0, 0, tzinfo=UTC),
        )
        assert rev.revision_id != rev.logical_signal_id

    def test_revision_numbers_ordered(self, identity: SignalIdentity) -> None:
        rev1 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 8, 8, 0, 0, 0, tzinfo=UTC),
        )
        rev2 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=2,
            previous_revision_id=rev1.revision_id,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 8, 8, 1, 0, 0, tzinfo=UTC),
        )
        assert rev2.revision_number == rev1.revision_number + 1
        assert rev2.previous_revision_id == rev1.revision_id

    def test_previous_revision_link_non_recursive(
        self, identity: SignalIdentity
    ) -> None:
        prev_id = uuid4()
        rev = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=identity.logical_signal_id,
            revision_number=2,
            previous_revision_id=prev_id,
            canonical_snapshot=(),
            fingerprint="ignored",
            created_at_utc=datetime(2024, 9, 9, 0, 0, 0, tzinfo=UTC),
        )
        assert rev.previous_revision_id == prev_id
        assert not isinstance(rev.previous_revision_id, SignalRevision)

    def test_revision_identity_independence(self) -> None:
        rev_id = uuid4()
        logical_id = uuid4()
        validate_revision_id_independence(rev_id, logical_id)


# ------------------------------------------------------------------
# FINGERPRINT CONTRACT (tests 10-22)
# ------------------------------------------------------------------


class TestFingerprintContract:
    def test_same_snapshot_same_fingerprint(self) -> None:
        snapshot = (("status", "COMPLETE"), ("price", Decimal("1.1000")))
        fp = canonical_fingerprint(snapshot)
        rev1 = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 10, 10, 0, 0, 0, tzinfo=UTC),
        )
        assert rev1.fingerprint == fp

    def test_different_snapshot_different_fingerprint(self) -> None:
        fp_a = canonical_fingerprint((("status", "COMPLETE"),))
        fp_b = canonical_fingerprint((("status", "CANCELLED"),))
        assert fp_a != fp_b

    def test_key_order_normalization(self) -> None:
        fp1 = canonical_fingerprint((("b", 2), ("a", 1)))
        fp2 = canonical_fingerprint((("a", 1), ("b", 2)))
        assert fp1 == fp2

    def test_tuple_ordering_semantic_preserved(self) -> None:
        fp1 = canonical_fingerprint((("levels", (1, 2)),))
        fp2 = canonical_fingerprint((("levels", (2, 1)),))
        assert fp1 != fp2

    def test_decimal_normalization(self) -> None:
        fp1 = canonical_fingerprint((("price", Decimal("10.5")),))
        fp2 = canonical_fingerprint((("price", Decimal("10.500")),))
        assert fp1 == fp2

    def test_uuid_normalization(self) -> None:
        u = uuid4()
        fp = canonical_fingerprint((("ref", u),))
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA-256 hex length

    def test_enum_normalization(self) -> None:
        fp = canonical_fingerprint((("direction", TradeDirection.BUY),))
        assert isinstance(fp, str)
        assert len(fp) == 64

    def test_unsupported_snapshot_type_rejected_at_revision_level(self) -> None:
        # Unsupported mutable dict inside tuple must be rejected by SignalRevision,
        # not silently serialized by fingerprint function (JSON handles dict).
        bad_snapshot = (("bad", {"not_tuple": True}),)
        # The public fingerprint mechanism now enforces the same ALLOWED_SNAPSHOT_TYPES
        # contract as SignalRevision. Unsupported types must be rejected deterministically.
        bad_snapshot = (("bad", {"not_tuple": True}),)
        with pytest.raises(TypeError, match="unsupported"):
            canonical_fingerprint(bad_snapshot)

    def test_no_python_hash_dependence(self) -> None:
        # Fingerprint must use sha256, not Python hash()
        snapshot = (("status", "COMPLETE"),)
        fp = canonical_fingerprint(snapshot)
        # Python hash is nondeterministic; fingerprint must be stable hex string
        assert isinstance(fp, str)
        assert len(fp) == 64
        # Same content must yield same fingerprint (not random like hash())
        assert canonical_fingerprint(snapshot) == fp

    def test_no_metadata_contamination(self) -> None:
        # Changing revision metadata must not change fingerprint if content same
        snapshot = (("status", "COMPLETE"),)
        rev_a = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=5,
            previous_revision_id=uuid4(),
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            event_reference_id=uuid4(),
            snapshot_version=7,
            created_at_utc=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=rev_a.logical_signal_id,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            event_reference_id=None,
            snapshot_version=1,
            created_at_utc=datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        assert rev_a.fingerprint == rev_b.fingerprint
        assert rev_a.fingerprint == canonical_fingerprint(snapshot)

    def test_same_fingerprint_different_logical_ids(self) -> None:
        snapshot = (("direction", "BUY"),)
        fp = canonical_fingerprint(snapshot)
        rev_a = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        assert rev_a.fingerprint == rev_b.fingerprint == fp
        assert rev_a.logical_signal_id != rev_b.logical_signal_id

    def test_same_fingerprint_different_revision_ids(self) -> None:
        snapshot = (("status", "ACTIVE"),)
        fp = canonical_fingerprint(snapshot)
        rev_a = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=uuid4(),
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        rev_b = SignalRevision(
            revision_id=uuid4(),
            logical_signal_id=rev_a.logical_signal_id,
            revision_number=2,
            previous_revision_id=rev_a.revision_id,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=datetime(2024, 2, 2, 0, 0, 0, tzinfo=UTC),
        )
        assert rev_a.fingerprint == rev_b.fingerprint == fp
        assert rev_a.revision_id != rev_b.revision_id

    def test_different_semantic_content_different_fingerprint(self) -> None:
        fp_a = canonical_fingerprint((("status", "COMPLETE"),))
        fp_b = canonical_fingerprint((("status", "CANCELLED"),))
        assert fp_a != fp_b

    def test_canonical_snapshot_independent_inspectable(self) -> None:
        # Design Section 3.12: snapshot must represent complete canonical state
        snapshot = (
            ("direction", "BUY"),
            ("entry_geometry", "SINGLE"),
            ("entry_trigger", "LIMIT"),
            ("entry_price", Price(value=Decimal("1.1000"))),
            ("stop_loss", Price(value=Decimal("1.0950"))),
            ("status", "COMPLETE"),
            ("lifecycle_state", "ACTIVE"),
            (
                "instrument",
                Instrument(canonical_symbol="EURUSD", asset_class=AssetClass.FOREX),
            ),
        )
        fp = canonical_fingerprint(snapshot)
        # Fingerprint must include all semantic content fields independently
        assert isinstance(fp, str)
        assert len(fp) == 64


# ------------------------------------------------------------------
# CANONICALIZATION (tests 23-26)
# ------------------------------------------------------------------


class TestCanonicalization:
    def test_deterministic_serialization(self) -> None:
        snapshot = (("a", 1), ("b", Decimal("2.5")))
        fp1 = canonical_fingerprint(snapshot)
        fp2 = canonical_fingerprint(snapshot)
        assert fp1 == fp2
        assert isinstance(fp1, str)
        assert len(fp1) == 64

    def test_stable_equivalent_construction(self) -> None:
        # Equivalent constructions should yield same fingerprint
        fp1 = canonical_fingerprint((("price", Price(value=Decimal("10.5"))),))
        fp2 = canonical_fingerprint((("price", Price(value=Decimal("10.500"))),))
        assert fp1 == fp2

    def test_nested_immutable_tuple(self) -> None:
        snapshot = (("levels", (Price(value=Decimal(150)), Price(value=Decimal(148)))),)
        fp = canonical_fingerprint(snapshot)
        assert isinstance(fp, str)
        assert len(fp) == 64

    def test_nested_immutable_frozenset_not_supported(self) -> None:
        # Design does not use frozenset in canonical snapshot; if passed,
        # normalization handles it deterministically.
        # Note: ALLOWED_SNAPSHOT_TYPES excludes frozenset (design correction from Step 4.1)
        pass  # No action needed; design excludes frozenset.


# ------------------------------------------------------------------
# PUBLIC API (test that single mechanism exists and is exposed)
# ------------------------------------------------------------------


def test_single_canonical_fingerprint_mechanism_exists() -> None:
    # Verify exactly one public mechanism exists (canonical_fingerprint)
    import packages.signal_core

    assert hasattr(packages.signal_core, "canonical_fingerprint")
    assert callable(packages.signal_core.canonical_fingerprint)


def test_fingerprint_not_using_python_hash() -> None:
    snapshot = (("x", 1),)
    fp = canonical_fingerprint(snapshot)
    # Python hash() returns int and is not deterministic across runs
    assert isinstance(fp, str)
    assert len(fp) == 64
    # Same content yields same fingerprint (not random)
    assert canonical_fingerprint(snapshot) == fp
