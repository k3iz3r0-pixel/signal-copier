from __future__ import annotations

from enum import Enum


class TradeDirection(Enum):
    """Trade direction (BUY / SELL)."""

    BUY = "BUY"
    SELL = "SELL"


class EntryGeometry(Enum):
    """Geometric structure of the entry (independent of execution trigger)."""

    MARKET = "MARKET"
    SINGLE = "SINGLE"
    RANGE = "RANGE"
    MULTIPLE = "MULTIPLE"


class EntryTrigger(Enum):
    """Execution / trigger semantics (independent of entry geometry)."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    UNSPECIFIED = "UNSPECIFIED"


class LifecycleState(Enum):
    """Minimal deterministic lifecycle state of the canonical signal itself."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class SignalStatus(Enum):
    """Completeness / ambiguity status of signal content."""

    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    AMBIGUOUS = "AMBIGUOUS"


class SourceType(Enum):
    """Generic ingestion source type (no Telegram-specific logic in core)."""

    TELEGRAM = "TELEGRAM"
    DISCORD = "DISCORD"
    MANUAL = "MANUAL"
    API = "API"


class EventType(Enum):
    """Separated event categories (lifecycle / modification / execution)."""

    CREATED = "CREATED"
    CANCELLED = "CANCELLED"
    INCOMPLETE_SIGNAL_RECEIVED = "INCOMPLETE_SIGNAL_RECEIVED"
    REVISED = "REVISED"
    SL_MOVED = "SL_MOVED"
    TP_MOVED = "TP_MOVED"
    BREAKEVEN = "BREAKEVEN"
    SCALE_IN = "SCALE_IN"
    REVERSAL = "REVERSAL"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    CLOSE_COMPLETE = "CLOSE_COMPLETE"
    SCALE_OUT = "SCALE_OUT"
    ARCHIVED = "ARCHIVED"


class InstructionType(Enum):
    """Canonical semantic instruction/action (not a broker Order)."""

    OPEN = "OPEN"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    CLOSE = "CLOSE"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    MOVE_SL = "MOVE_SL"
    MOVE_TP = "MOVE_TP"
    BREAKEVEN = "BREAKEVEN"
    TRAIL = "TRAIL"
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"
    REVERSE = "REVERSE"


class AssetClass(Enum):
    """Provider-agnostic asset class for Instrument identity."""

    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    STOCK = "STOCK"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    BOND = "BOND"
    ETF = "ETF"
    OTHER = "OTHER"
