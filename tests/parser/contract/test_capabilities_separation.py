"""Provider capability / rule separation (design §12.4, ADR 0011).

``ProviderCapabilities`` declares ONLY what a provider can express (19 booleans).
Syntax and lexical specifics (keywords, separators, decimal/range formats,
matcher/scope) belong to ``ProviderProfile`` and ``ProviderRule`` — never to
capability flags.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from packages.parser import (
    MatcherSpec,
    ProviderCapabilities,
    ProviderProfile,
    ProviderRule,
    RuleSet,
    ScopeSpec,
)
from packages.parser.enums import (
    DeleteBehavior,
    EditBehavior,
    FollowUpBehavior,
    MatcherKind,
    OccurrenceSelection,
    ReplyRequirement,
    ScopeKind,
    SemanticTarget,
)

EXPECTED_CAPABILITY_FLAGS = (
    "close_full",
    "close_half",
    "profit_close",
    "move_sl_breakeven",
    "remove_sl",
    "cancel_pending",
    "trigger_pending",
    "move_sl_number",
    "move_sl_conditional",
    "move_tp_conditional",
    "move_entry_conditional",
    "edit_handling",
    "delete_handling",
    "reply_required",
    "negative_keywords",
    "last_signal_execution",
    "trailing",
    "multi_signal",
    "multi_message",
)


def _caps(**overrides: bool) -> ProviderCapabilities:
    defaults = {name: False for name in EXPECTED_CAPABILITY_FLAGS}
    defaults.update(overrides)
    return ProviderCapabilities(**defaults)


def test_capabilities_have_exactly_19_documented_boolean_flags() -> None:
    field_names = tuple(
        f.name for f in ProviderCapabilities.__dataclass_fields__.values()
    )
    assert field_names == EXPECTED_CAPABILITY_FLAGS
    assert len(field_names) == 19


def test_capability_fields_require_bool() -> None:
    with pytest.raises(TypeError):
        _caps(close_full=1)  # type: ignore[arg-type]


def test_capabilities_have_no_syntax_fields() -> None:
    """Capabilities are capability-oriented (§12.4): no keyword/separator/
    pattern/matcher/scope fields may leak into the flag set."""
    field_names = {f.name for f in ProviderCapabilities.__dataclass_fields__.values()}
    syntax_terms = {
        "tokenizer_pattern",
        "decimal_format",
        "field_separators",
        "multi_value_separators",
        "range_patterns",
        "matcher",
        "scope",
        "patterns",
        "keywords",
    }
    assert field_names.isdisjoint(syntax_terms)


def test_capabilities_and_rules_are_distinct_fields_on_profile() -> None:
    capabilities = _caps(close_half=True, move_sl_number=True)
    rule = ProviderRule(
        id="provider_alpha.sl.move",
        category="SL",
        matcher=MatcherSpec(kind=MatcherKind.LITERAL, params=(("text", "SL"),)),
        scope=ScopeSpec(kind=ScopeKind.WHOLE_MESSAGE),
        constraints=(),
        target=SemanticTarget.SL,
        priority=0,
        occurrence=OccurrenceSelection.FIRST,
    )
    rule_set = RuleSet(rules=(rule,))
    profile = ProviderProfile(
        provider_name="provider_alpha",
        capabilities=capabilities,
        rule_set=rule_set,
        symbol_aliases=(("GOLD", "XAUUSD"),),
        tokenizer_pattern=r"(?P<number>\d+(?:\.\d+)?)",
        field_separators=(",",),
        multi_value_separators=("/",),
        decimal_format=r"\d+(?:\.\d+)?",
        range_patterns=("-",),
        multiline_mode=False,
        reply_requirement=ReplyRequirement.NONE,
        edit_behavior=EditBehavior.REPARSE_DELTA,
        delete_behavior=DeleteBehavior.CANCEL_TARGET,
        follow_up_behavior=FollowUpBehavior.TARGET_LAST_SIGNAL,
        version="1",
    )
    assert profile.capabilities.close_half is True
    assert profile.capabilities.move_sl_number is True
    assert profile.rule_set.rules[0].matcher.kind == MatcherKind.LITERAL
    assert profile.max_message_length == 8000
    assert profile.max_numeric_value == Decimal("1e12")
