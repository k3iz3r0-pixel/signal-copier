"""Enum validity contract for the Phase 2 parser (design §26.1).

Verifies every Phase 2 enum has exactly the documented members, in the
documented order, with stable string values equal to the member names. Phase 1
enums are imported verbatim and are therefore outside this test's scope.
"""

from __future__ import annotations

from enum import Enum

import pytest

from packages.parser import (
    AmbiguityKind,
    CandidateSlot,
    ConditionKind,
    ConflictKind,
    Constraint,
    ContextReferenceKind,
    ContextRequirement,
    CorrelationRequestKind,
    DeleteBehavior,
    EditBehavior,
    FollowUpBehavior,
    FragmentState,
    MatcherKind,
    MediaKind,
    MessageEvent,
    OccurrenceSelection,
    ParseResultState,
    ReplyRequirement,
    ScopeKind,
    SemanticTarget,
    TokenCategory,
)

EXPECTED_MEMBERS: dict[type[Enum], tuple[str, ...]] = {
    ParseResultState: (
        "PARSED",
        "PARTIAL",
        "AMBIGUOUS",
        "MALFORMED",
        "UNSUPPORTED",
        "NO_SIGNAL",
        "MULTI_SIGNAL",
    ),
    MessageEvent: ("CREATE", "EDIT", "DELETE", "FOLLOW_UP"),
    MediaKind: ("IMAGE", "VIDEO", "DOCUMENT", "NONE"),
    TokenCategory: (
        "NUMBER",
        "KEYWORD",
        "SYMBOL",
        "PUNCT",
        "WHITESPACE",
        "TEXT",
        "EMOJI",
    ),
    CandidateSlot: (
        "DIRECTION",
        "INSTRUMENT",
        "ENTRY",
        "ENTRY_GEOMETRY",
        "ENTRY_TRIGGER",
        "SL",
        "TP",
        "ACTION",
        "CONDITION",
        "METADATA",
        "PRICE",
        "RANGE",
    ),
    FragmentState: ("RESOLVED", "UNRESOLVED", "CONDITIONAL"),
    ConditionKind: ("IN_PROFIT", "AT_PRICE", "KEYWORD_PRESENT", "NONE"),
    ConflictKind: ("CONFLICTING",),
    AmbiguityKind: ("AMBIGUOUS_TRIGGER", "AMBIGUOUS_RANGE", "AMBIGUOUS_PERCENT"),
    ContextReferenceKind: (
        "REPLY",
        "QUOTE",
        "LAST_SIGNAL",
        "EDITED_ORIGINAL",
        "NONE",
    ),
    ContextRequirement: (
        "NONE",
        "REPLY_REQUIRED",
        "CONTEXT_REQUIRED",
        "LAST_SIGNAL",
    ),
    CorrelationRequestKind: (
        "TARGET_LAST_SIGNAL",
        "TARGET_REPLIED_SIGNAL",
        "MULTI_MESSAGE_APPEND",
        "EDIT_APPLY",
        "DELETE_APPLY",
        "NONE",
    ),
    MatcherKind: (
        "LITERAL",
        "REGEX",
        "TOKEN_SEQUENCE",
        "SYMBOL",
        "ALIAS",
        "NUMBER",
        "PRICE",
        "PRICE_RANGE",
    ),
    ScopeKind: (
        "WHOLE_MESSAGE",
        "LINE",
        "SECTION",
        "AFTER_TOKEN",
        "BEFORE_TOKEN",
        "BETWEEN_ANCHORS",
        "REPLY",
        "QUOTED_MESSAGE",
    ),
    SemanticTarget: (
        "DIRECTION",
        "INSTRUMENT",
        "ENTRY",
        "ENTRY_GEOMETRY",
        "ENTRY_TRIGGER",
        "SL",
        "TP",
        "ACTION",
        "CONDITION",
        "METADATA",
    ),
    OccurrenceSelection: ("FIRST", "LAST", "NTH", "ALL"),
    Constraint: (
        "REQUIRES",
        "FORBIDS",
        "REQUIRED",
        "REQUIRES_REPLY",
        "REQUIRES_CONTEXT",
        "MUTUALLY_EXCLUSIVE",
        "REPEATABLE",
        "UNIQUENESS",
    ),
    ReplyRequirement: ("NONE", "REQUIRED", "OPTIONAL"),
    EditBehavior: ("REPARSE_DELTA", "IGNORE"),
    DeleteBehavior: ("CANCEL_TARGET", "IGNORE"),
    FollowUpBehavior: ("TARGET_LAST_SIGNAL", "IGNORE"),
}


@pytest.mark.parametrize(
    "enum_cls,members",
    [
        pytest.param(cls, members, id=cls.__name__)
        for cls, members in EXPECTED_MEMBERS.items()
    ],
)
def test_enum_members_exact(enum_cls: type[Enum], members: tuple[str, ...]) -> None:
    """Each Phase 2 enum has exactly the documented members in order."""
    assert [m.name for m in enum_cls] == list(members)


@pytest.mark.parametrize(
    "enum_cls",
    [pytest.param(cls, id=cls.__name__) for cls in EXPECTED_MEMBERS],
)
def test_enum_values_equal_member_names(enum_cls: type[Enum]) -> None:
    """Every member's value is its own name (stable string identity)."""
    for member in enum_cls:
        assert member.value == member.name


def test_all_21_phase2_enums_present() -> None:
    """The registry enumerates exactly 21 Phase 2 enums (§26.1)."""
    assert len(EXPECTED_MEMBERS) == 21
