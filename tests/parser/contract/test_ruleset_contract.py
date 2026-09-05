"""RuleSet structural invariants + representation contract (design §5.18, §12.5).

Covers Phase 2A brief item 8 (RuleSet structural invariants) and the RULESET
REQUIREMENT: the contract REPRESENTS provider rules, inherited rules
(``parent``), ``inherited_rule_id`` (``overrides``), exclusions, rule identity
(``ProviderRule.id``), and version compatibility (``ProviderProfile.version``).

The deterministic effective-RuleSet RESOLUTION algorithm (linearization, chain
folding, chain-level validation) is Phase 3+ engine behaviour and is
intentionally NOT tested here. Rule EXECUTION (matching) is also out of scope.
"""

from __future__ import annotations

import pytest

from packages.parser import (
    MatcherSpec,
    ProviderRule,
    RuleSet,
    RuleSetResolutionError,
    ScopeSpec,
)
from packages.parser.enums import (
    MatcherKind,
    OccurrenceSelection,
    ScopeKind,
    SemanticTarget,
)


def _rule(rule_id: str, category: str = "ENTRY", priority: int = 0) -> ProviderRule:
    return ProviderRule(
        id=rule_id,
        category=category,
        matcher=MatcherSpec(kind=MatcherKind.LITERAL, params=(("text", rule_id),)),
        scope=ScopeSpec(kind=ScopeKind.WHOLE_MESSAGE),
        constraints=(),
        target=SemanticTarget.ENTRY,
        priority=priority,
        occurrence=OccurrenceSelection.FIRST,
    )


# ---------------------------------------------------------------------------
# Representation contract: exactly the documented fields (§5.18)
# ---------------------------------------------------------------------------


def test_ruleset_has_exactly_the_documented_fields() -> None:
    field_names = tuple(f.name for f in RuleSet.__dataclass_fields__.values())
    assert field_names == ("rules", "parent", "overrides", "exclusions")


def test_provider_rule_id_is_the_rule_identity() -> None:
    """Rule identity is ``ProviderRule.id`` (stable, non-empty string)."""
    with pytest.raises(ValueError):
        _rule("")
    assert (
        _rule("provider_alpha.entry.buy_limit").id == "provider_alpha.entry.buy_limit"
    )


def test_ruleset_represents_inheritance_and_override_fields() -> None:
    rule_set = RuleSet(
        rules=(_rule("a"), _rule("b")),
        parent="common",
        overrides=(("b", "inherited_b"),),
        exclusions=("inherited_x",),
    )
    assert rule_set.parent == "common"
    assert rule_set.overrides == (("b", "inherited_b"),)
    assert rule_set.exclusions == ("inherited_x",)


# ---------------------------------------------------------------------------
# Construction-time structural invariants (§12.5 — own-level only)
# ---------------------------------------------------------------------------


def test_duplicate_rule_id_within_one_ruleset_rejected() -> None:
    with pytest.raises(RuleSetResolutionError) as exc_info:
        RuleSet(rules=(_rule("a"), _rule("a")))
    assert exc_info.value.code == "duplicate_rule_id"


def test_exclusion_naming_own_declaration_rejected() -> None:
    with pytest.raises(RuleSetResolutionError) as exc_info:
        RuleSet(rules=(_rule("a"),), exclusions=("a",))
    assert exc_info.value.code == "exclusion_conflicts_with_declaration"


def test_duplicate_exclusion_entries_rejected() -> None:
    with pytest.raises(RuleSetResolutionError) as exc_info:
        RuleSet(rules=(_rule("a"),), exclusions=("x", "x"))
    assert exc_info.value.code == "exclusion_conflicts_with_declaration"


def test_override_rule_id_must_be_declared_in_own_rules() -> None:
    with pytest.raises(RuleSetResolutionError) as exc_info:
        RuleSet(rules=(_rule("a"),), overrides=(("missing", "base"),))
    assert exc_info.value.code == "conflicting_override"


def test_override_duplicate_rule_id_rejected() -> None:
    with pytest.raises(RuleSetResolutionError) as exc_info:
        RuleSet(rules=(_rule("a"), _rule("b")), overrides=(("a", "x"), ("a", "y")))
    assert exc_info.value.code == "conflicting_override"


def test_override_duplicate_inherited_target_rejected() -> None:
    with pytest.raises(RuleSetResolutionError) as exc_info:
        RuleSet(rules=(_rule("a"), _rule("b")), overrides=(("a", "x"), ("b", "x")))
    assert exc_info.value.code == "conflicting_override"


def test_ruleset_valid() -> None:
    rule_set = RuleSet(rules=(_rule("a"), _rule("b")), parent="common")
    assert rule_set.parent == "common"
    assert [r.id for r in rule_set.rules] == ["a", "b"]
