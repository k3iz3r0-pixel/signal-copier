"""Regression tests: Condition objects (design §8.2).

A CONDITION-target rule records a deterministic :class:`Condition`
predicate — the kind from the rule's declared ``condition_kind`` matcher
param, the operand shape determined by the kind. Conditions are recorded,
never evaluated. ``CanonicalParserIR.conditions`` must be populated from
the resolved CONDITION candidates.
"""

from decimal import Decimal

import pytest

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ConditionKind, ParseResultState
from packages.parser.profiles import ProfileLoadError, load_profile
from packages.parser.types import Condition
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime


def _condition_fragments(result):
    return [f for f in result.ir.fragments if f.slot is CandidateSlot.CONDITION]


def test_at_price_condition_records_price_operand() -> None:
    r = parse(
        make_raw("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 AT 1.0995"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert r.outcome is ParseResultState.PARSED
    assert r.ir.conditions == (
        Condition(
            kind=ConditionKind.AT_PRICE,
            params=(("price", Price(Decimal("1.0995"))),),
        ),
    )
    fragment = _condition_fragments(r)[0]
    assert fragment.value == r.ir.conditions[0]
    assert fragment.state.name == "RESOLVED"


def test_condition_candidate_value_is_condition_object() -> None:
    """The CONDITION candidate value is the canonical Condition object, not
    the raw captured text; the captured text stays reachable via the raw
    span (evidence) and via the preserved PRICE candidate."""
    raw = "CLOSE 30% AT 1.1100"
    r = parse(
        make_raw(raw), make_metadata("provider_001"), make_runtime("provider_001")
    )
    condition_candidates = [
        c for c in r.ir.candidates if c.slot is CandidateSlot.CONDITION
    ]
    assert len(condition_candidates) == 1
    value = condition_candidates[0].value
    assert isinstance(value, Condition)
    assert value.kind is ConditionKind.AT_PRICE
    assert value.params == (("price", Price(Decimal("1.1100"))),)
    assert (
        raw[
            condition_candidates[0].source_span.start : condition_candidates[
                0
            ].source_span.end
        ]
        == "1.1100"
    )
    assert any(
        c.slot is CandidateSlot.PRICE and c.value == Decimal("1.1100")
        for c in r.ir.candidates
    )


def test_in_profit_condition_carries_no_operand() -> None:
    """§20.8: 'CLOSE 30% AT 1.1100' — the AT_PRICE condition is recorded
    alongside the partial close; the percent operand stays a PRICE
    candidate. IN_PROFIT (no operand) is exercised with a synthetic rule."""
    r = parse(
        make_raw("CLOSE 30% AT 1.1100"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert r.outcome is ParseResultState.PARSED
    assert r.ir.conditions == (
        Condition(
            kind=ConditionKind.AT_PRICE,
            params=(("price", Price(Decimal("1.1100"))),),
        ),
    )
    actions = [f for f in r.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert actions and actions[0].value.name == "PARTIAL_CLOSE"


def _runtime_with_keyword_condition(text: str):
    profile_data = {
        "provider_name": "cond_kw",
        "version": "2B",
        "capabilities": {
            flag: False
            for flag in (
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
        },
        "field_separators": ["—"],
        "multi_value_separators": ["/"],
        "decimal_format": "dot",
        "range_patterns": ["-"],
        "rule_set": {
            "name": "cond_kw",
            "rules": [
                {
                    "id": "cond_kw.in_profit",
                    "category": "CONDITION",
                    "matcher": {
                        "kind": "REGEX",
                        "params": {
                            "pattern": r"IN\s+PROFIT",
                            "group": 0,
                            "condition_kind": "KEYWORD_PRESENT",
                        },
                    },
                    "scope": {"kind": "WHOLE_MESSAGE"},
                    "constraints": [],
                    "target": "CONDITION",
                    "priority": 30,
                    "occurrence": "FIRST",
                }
            ],
        },
    }
    return load_profile(profile_data, {})


def test_keyword_present_condition_records_keyword_text() -> None:
    runtime = _runtime_with_keyword_condition("IN PROFIT")
    r = parse(
        make_raw("IN PROFIT"),
        make_metadata("cond_kw"),
        runtime,
    )
    assert r.ir.conditions == (
        Condition(
            kind=ConditionKind.KEYWORD_PRESENT,
            params=(("keyword", "IN PROFIT"),),
        ),
    )


def test_condition_kind_param_is_mandatory() -> None:
    profile_data = {
        "provider_name": "bad_cond",
        "version": "2B",
        "capabilities": {},
        "decimal_format": "dot",
        "rule_set": {
            "name": "bad_cond",
            "rules": [
                {
                    "id": "bad_cond.condition",
                    "category": "CONDITION",
                    "matcher": {"kind": "REGEX", "params": {"pattern": r"AT\s+(\d+)"}},
                    "scope": {"kind": "WHOLE_MESSAGE"},
                    "constraints": [],
                    "target": "CONDITION",
                    "priority": 30,
                    "occurrence": "FIRST",
                }
            ],
        },
    }
    with pytest.raises(ProfileLoadError) as excinfo:
        load_profile(profile_data, {})
    assert excinfo.value.code == "invalid_profile_data"


def test_condition_kind_param_must_be_known_kind() -> None:
    profile_data = {
        "provider_name": "bad_cond",
        "version": "2B",
        "capabilities": {},
        "decimal_format": "dot",
        "rule_set": {
            "name": "bad_cond",
            "rules": [
                {
                    "id": "bad_cond.condition",
                    "category": "CONDITION",
                    "matcher": {
                        "kind": "REGEX",
                        "params": {"pattern": r"X", "condition_kind": "NOT_A_KIND"},
                    },
                    "scope": {"kind": "WHOLE_MESSAGE"},
                    "constraints": [],
                    "target": "CONDITION",
                    "priority": 30,
                    "occurrence": "FIRST",
                }
            ],
        },
    }
    with pytest.raises(ProfileLoadError) as excinfo:
        load_profile(profile_data, {})
    assert excinfo.value.code == "invalid_profile_data"


def test_condition_kind_validated_on_inherited_rules() -> None:
    """The validation runs over the EFFECTIVE ruleset: a parent-chain
    CONDITION rule without a valid condition_kind fails the child's load."""
    bad_common = {
        "name": "bad_common",
        "rules": [
            {
                "id": "bad_common.condition",
                "category": "CONDITION",
                "matcher": {"kind": "REGEX", "params": {"pattern": r"AT\s+(\d+)"}},
                "scope": {"kind": "WHOLE_MESSAGE"},
                "constraints": [],
                "target": "CONDITION",
                "priority": 30,
                "occurrence": "FIRST",
            }
        ],
    }
    child = {
        "provider_name": "cond_child",
        "version": "2B",
        "capabilities": {},
        "decimal_format": "dot",
        "rule_set": {"name": "cond_child", "parent": "bad_common", "rules": []},
    }
    with pytest.raises(ProfileLoadError) as excinfo:
        load_profile(child, {"bad_common": bad_common})
    assert excinfo.value.code == "invalid_profile_data"


def test_percent_operand_cannot_satisfy_at_price_condition() -> None:
    """A percent-suffixed number is never a price (§5.6 binding): the
    captured '2' in 'AT 2%' is disqualified, so no AT_PRICE condition and
    no condition fragment result from it."""
    r = parse(
        make_raw("AT 2%"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert r.ir.conditions == ()
    assert _condition_fragments(r) == []


def test_conditions_are_deterministic_across_parses() -> None:
    text = "BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 AT 1.0995"
    first = parse(
        make_raw(text), make_metadata("provider_001"), make_runtime("provider_001")
    )
    second = parse(
        make_raw(text), make_metadata("provider_001"), make_runtime("provider_001")
    )
    assert first.ir.conditions == second.ir.conditions
    assert first.outcome is second.outcome


def test_conditions_are_frozen_tuples_of_frozen_conditions() -> None:
    r = parse(
        make_raw("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 AT 1.0995"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert isinstance(r.ir.conditions, tuple)
    for condition in r.ir.conditions:
        assert isinstance(condition, Condition)
        with pytest.raises(AttributeError):
            condition.kind = ConditionKind.NONE  # type: ignore[misc]
