"""Phase 2 parser enums (authoritative registry: design §26.1).

These are the only enums the parser may introduce. Every Phase 1 enum
(TradeDirection, EntryGeometry, EntryTrigger, LifecycleState, SignalStatus,
EventType, InstructionType, SourceType, AssetClass) is IMPORTED verbatim and is
never extended by the parser (design §4.3, §26.1).
"""

from __future__ import annotations

from enum import Enum


class ParseResultState(Enum):
    """Discrete parse outcomes (design §14.1; ADR 0013 adds MULTI_SIGNAL
    for sectioned multi-block messages)."""

    PARSED = "PARSED"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    MALFORMED = "MALFORMED"
    UNSUPPORTED = "UNSUPPORTED"
    NO_SIGNAL = "NO_SIGNAL"
    MULTI_SIGNAL = "MULTI_SIGNAL"


class BlockSeparatorKind(Enum):
    """How a message block is separated from its predecessor (ADR 0013).

    Dividers are profile-declared strong separators; blank-line runs act
    as weak separators only inside sectioned messages (messages that
    contain at least one divider — ordinary single-signal messages are
    full of blank lines, ADR 0013 audit)."""

    NONE = "NONE"
    DIVIDER = "DIVIDER"
    BLANK_LINE = "BLANK_LINE"


class MessageEvent(Enum):
    """Message lifecycle, separate from Signal lifecycle (design §9.1)."""

    CREATE = "CREATE"
    EDIT = "EDIT"
    DELETE = "DELETE"
    FOLLOW_UP = "FOLLOW_UP"


class MediaKind(Enum):
    """Media reference kind (design §5.1). Media is never opened by the parser."""

    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    NONE = "NONE"


class TokenCategory(Enum):
    """Lexical unit categories produced by Lexical Analysis (design §5.4)."""

    NUMBER = "NUMBER"
    KEYWORD = "KEYWORD"
    SYMBOL = "SYMBOL"
    PUNCT = "PUNCT"
    WHITESPACE = "WHITESPACE"
    TEXT = "TEXT"
    EMOJI = "EMOJI"


class CandidateSlot(Enum):
    """Competing-hypothesis semantic slots (design §5.6)."""

    DIRECTION = "DIRECTION"
    INSTRUMENT = "INSTRUMENT"
    ENTRY = "ENTRY"
    ENTRY_GEOMETRY = "ENTRY_GEOMETRY"
    ENTRY_TRIGGER = "ENTRY_TRIGGER"
    SL = "SL"
    TP = "TP"
    ACTION = "ACTION"
    CONDITION = "CONDITION"
    METADATA = "METADATA"
    PRICE = "PRICE"
    RANGE = "RANGE"


class FragmentState(Enum):
    """Resolution state of a ParsedFragment (design §5.12)."""

    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    CONDITIONAL = "CONDITIONAL"


class ConditionKind(Enum):
    """Deterministic condition predicates, recorded but never evaluated (design §8.2)."""

    IN_PROFIT = "IN_PROFIT"
    AT_PRICE = "AT_PRICE"
    KEYWORD_PRESENT = "KEYWORD_PRESENT"
    NONE = "NONE"


class ConflictKind(Enum):
    """Contradiction between competing candidates (design §5.10)."""

    CONFLICTING = "CONFLICTING"


class AmbiguityKind(Enum):
    """Genuine underdetermination the parser cannot resolve (design §5.11)."""

    AMBIGUOUS_TRIGGER = "AMBIGUOUS_TRIGGER"
    AMBIGUOUS_RANGE = "AMBIGUOUS_RANGE"
    AMBIGUOUS_PERCENT = "AMBIGUOUS_PERCENT"


class ContextReferenceKind(Enum):
    """How a message references a prior message/signal (design §5.20)."""

    REPLY = "REPLY"
    QUOTE = "QUOTE"
    LAST_SIGNAL = "LAST_SIGNAL"
    EDITED_ORIGINAL = "EDITED_ORIGINAL"
    NONE = "NONE"


class ContextRequirement(Enum):
    """Context needed to resolve a fragment (design §5.12)."""

    NONE = "NONE"
    REPLY_REQUIRED = "REPLY_REQUIRED"
    CONTEXT_REQUIRED = "CONTEXT_REQUIRED"
    LAST_SIGNAL = "LAST_SIGNAL"


class CorrelationRequestKind(Enum):
    """What the parser asks the correlation layer to do (design §5.21)."""

    TARGET_LAST_SIGNAL = "TARGET_LAST_SIGNAL"
    TARGET_REPLIED_SIGNAL = "TARGET_REPLIED_SIGNAL"
    MULTI_MESSAGE_APPEND = "MULTI_MESSAGE_APPEND"
    EDIT_APPLY = "EDIT_APPLY"
    DELETE_APPLY = "DELETE_APPLY"
    NONE = "NONE"


class MatcherKind(Enum):
    """Matcher primitives for ProviderRule (design §7.1)."""

    LITERAL = "LITERAL"
    REGEX = "REGEX"
    TOKEN_SEQUENCE = "TOKEN_SEQUENCE"
    SYMBOL = "SYMBOL"
    ALIAS = "ALIAS"
    NUMBER = "NUMBER"
    PRICE = "PRICE"
    PRICE_RANGE = "PRICE_RANGE"


class ScopeKind(Enum):
    """Match scope primitives for ProviderRule (design §7.1)."""

    WHOLE_MESSAGE = "WHOLE_MESSAGE"
    LINE = "LINE"
    SECTION = "SECTION"
    AFTER_TOKEN = "AFTER_TOKEN"
    BEFORE_TOKEN = "BEFORE_TOKEN"
    BETWEEN_ANCHORS = "BETWEEN_ANCHORS"
    REPLY = "REPLY"
    QUOTED_MESSAGE = "QUOTED_MESSAGE"


class SemanticTarget(Enum):
    """Semantic targets a rule can bind (design §7.1)."""

    DIRECTION = "DIRECTION"
    INSTRUMENT = "INSTRUMENT"
    ENTRY = "ENTRY"
    ENTRY_GEOMETRY = "ENTRY_GEOMETRY"
    ENTRY_TRIGGER = "ENTRY_TRIGGER"
    SL = "SL"
    TP = "TP"
    ACTION = "ACTION"
    CONDITION = "CONDITION"
    METADATA = "METADATA"


class OccurrenceSelection(Enum):
    """Which occurrence a rule binds (design §7.2)."""

    FIRST = "FIRST"
    LAST = "LAST"
    NTH = "NTH"
    ALL = "ALL"


class Constraint(Enum):
    """Rule-fire constraints (design §7.1)."""

    REQUIRES = "REQUIRES"
    FORBIDS = "FORBIDS"
    REQUIRED = "REQUIRED"
    REQUIRES_REPLY = "REQUIRES_REPLY"
    REQUIRES_CONTEXT = "REQUIRES_CONTEXT"
    MUTUALLY_EXCLUSIVE = "MUTUALLY_EXCLUSIVE"
    REPEATABLE = "REPEATABLE"
    UNIQUENESS = "UNIQUENESS"


class ReplyRequirement(Enum):
    """Profile-level reply requirement (design §5.15)."""

    NONE = "NONE"
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class EditBehavior(Enum):
    """Profile-level edit handling (design §5.15)."""

    REPARSE_DELTA = "REPARSE_DELTA"
    IGNORE = "IGNORE"


class DeleteBehavior(Enum):
    """Profile-level deletion handling (design §5.15)."""

    CANCEL_TARGET = "CANCEL_TARGET"
    IGNORE = "IGNORE"


class FollowUpBehavior(Enum):
    """Profile-level follow-up handling (design §5.15)."""

    TARGET_LAST_SIGNAL = "TARGET_LAST_SIGNAL"
    IGNORE = "IGNORE"
