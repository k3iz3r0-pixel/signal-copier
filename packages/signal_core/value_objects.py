from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from packages.signal_core.enums import AssetClass, SourceType


@dataclass(frozen=True, slots=True)
class Price:
    """Immutable financial price using Decimal (float banned)."""

    value: Decimal
    currency: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError(
                f"Price.value must be Decimal, got {type(self.value).__name__}"
            )
        if isinstance(self.value, float):
            # Explicit guard against accidental float assignment
            raise TypeError("Price.value must be Decimal; float is banned from domain")

    def __str__(self) -> str:
        return f"Price(value={self.value})"


@dataclass(frozen=True, slots=True)
class PriceRange:
    """Entry range with low/high boundaries (both Optional[Price])."""

    low: Price | None = None
    high: Price | None = None

    def __post_init__(self) -> None:
        if self.low is not None and not isinstance(self.low, Price):
            raise TypeError("PriceRange.low must be Price or None")
        if self.high is not None and not isinstance(self.high, Price):
            raise TypeError("PriceRange.high must be Price or None")
        if self.low is None and self.high is None:
            raise ValueError(
                "PriceRange must have at least one boundary (low or high) present"
            )
        # Invariant: when both present, low.value <= high.value (not enforced in Phase 1 per design)


@dataclass(frozen=True, slots=True)
class ProviderSource:
    """Provider and ingestion provenance (frozen, no mutable fields)."""

    provider_name: str
    signal_reference: str
    ingestion_timestamp_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider_name, str) or not self.provider_name:
            raise ValueError("provider_name must be a non-empty string")
        if not isinstance(self.signal_reference, str) or not self.signal_reference:
            raise ValueError("signal_reference must be a non-empty string")


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Ingestion source identity separate from provider identity."""

    source_type: SourceType
    source_reference: str | None = None
    ingestion_timestamp_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, SourceType):
            raise TypeError("source_type must be SourceType enum member")
        if self.source_reference is not None and (
            not isinstance(self.source_reference, str) or not self.source_reference
        ):
            raise ValueError("source_reference must be non-empty string when provided")


@dataclass(frozen=True, slots=True)
class Instrument:
    """Provider-agnostic instrument identity (canonical_symbol + asset_class)."""

    canonical_symbol: str
    asset_class: AssetClass

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_symbol, str) or not self.canonical_symbol:
            raise ValueError("canonical_symbol must be a non-empty string")
        if not isinstance(self.asset_class, AssetClass):
            raise TypeError("asset_class must be AssetClass enum member")
