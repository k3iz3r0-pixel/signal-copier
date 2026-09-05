"""Regression tests: action capability flags (design §20.10-§20.12).

The flags that distinguish otherwise identical InstructionType values —
``remove_sl`` for REMOVE SL vs a generic MOVE_SL, ``cancel_pending`` for
CANCEL PENDING, ``trigger_pending`` for TRIGGER PENDING (a MODIFY) — are
recorded on the ACTION fragment as ``action_flags`` evidence, derived
deterministically from the rule's category (CATEGORY_CAPABILITY) and from
any explicitly declared ``flags`` matcher param.
"""

from packages.parser import parse
from packages.parser.enums import CandidateSlot, ParseResultState
from packages.parser.profiles import load_profile
from packages.parser.types import MatchEvidence, ProviderCapabilities
from tests.parser._helpers import make_metadata, make_raw, make_runtime

_ALL_OFF = {flag: False for flag in ProviderCapabilities.__dataclass_fields__}


def _action_fragment(result):
    fragments = [f for f in result.ir.fragments if f.slot is CandidateSlot.ACTION]
    assert fragments, "no ACTION fragment"
    return fragments[0]


def _action_flags(fragment) -> dict[str, object]:
    entries: dict[str, object] = {}
    for evidence in fragment.evidence:
        if evidence.kind == "action_flags":
            for key, value in evidence.fields:
                entries[str(key)] = value
    return entries


def test_remove_sl_records_remove_sl_flag() -> None:
    """§20.10: 'REMOVE SL' -> instruction_type=MOVE_SL, remove_sl=True."""
    r = parse(
        make_raw("REMOVE SL"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert r.outcome is ParseResultState.NO_SIGNAL
    fragment = _action_fragment(r)
    assert fragment.value.name == "MOVE_SL"
    assert _action_flags(fragment) == {"remove_sl": True}


def test_cancel_pending_records_cancel_pending_flag() -> None:
    """§20.11: 'CANCEL PENDING' -> instruction_type=CANCEL, cancel_pending=True."""
    r = parse(
        make_raw("CANCEL PENDING"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert r.outcome is ParseResultState.PARSED
    fragment = _action_fragment(r)
    assert fragment.value.name == "CANCEL"
    assert _action_flags(fragment) == {"cancel_pending": True}


def test_trigger_pending_records_trigger_pending_flag() -> None:
    """§20.12: 'TRIGGER PENDING NOW' -> instruction_type=MODIFY,
    trigger_pending=True (TRIGGER_PENDING InstructionType is an open
    question, §24 — the flag carries the distinction)."""
    r = parse(
        make_raw("TRIGGER PENDING NOW"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert r.outcome is ParseResultState.PARSED
    fragment = _action_fragment(r)
    assert fragment.value.name == "MODIFY"
    assert _action_flags(fragment) == {"trigger_pending": True}


def test_move_sl_number_flag_distinguishes_number_change_from_remove() -> None:
    """'SL 3320' (follow-up) is MOVE_SL via move_sl_number; the
    remove_sl flag must NOT appear on it."""
    r = parse(
        make_raw("SL 3320"), make_metadata("provider_001"), make_runtime("provider_001")
    )
    fragment = _action_fragment(r)
    assert fragment.value.name == "MOVE_SL"
    assert _action_flags(fragment) == {"move_sl_number": True}


def test_breakeven_records_move_sl_breakeven_flag() -> None:
    r = parse(
        make_raw("MOVE SL TO BE"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    fragment = _action_fragment(r)
    assert fragment.value.name == "BREAKEVEN"
    assert _action_flags(fragment) == {"move_sl_breakeven": True}


def _explicit_flags_runtime():
    profile_data = {
        "provider_name": "flagged",
        "version": "2B",
        "capabilities": {**_ALL_OFF, "close_full": True},
        "field_separators": ["—"],
        "multi_value_separators": ["/"],
        "decimal_format": "dot",
        "range_patterns": ["-"],
        "rule_set": {
            "name": "flagged",
            "rules": [
                {
                    "id": "flagged.close",
                    "category": "ACTION_CLOSE",
                    "matcher": {
                        "kind": "REGEX",
                        "params": {
                            "pattern": r"CLOSE",
                            "ignore_case": True,
                            "flags": {"origin": "explicit"},
                        },
                    },
                    "scope": {"kind": "WHOLE_MESSAGE"},
                    "constraints": [],
                    "target": "ACTION",
                    "priority": 20,
                    "occurrence": "FIRST",
                }
            ],
        },
    }
    return load_profile(profile_data, {})


def test_declared_flags_merge_with_category_derived_flags() -> None:
    """Declared ``flags`` entries come first, category-derived entries are
    appended — deterministic ordering."""
    runtime = _explicit_flags_runtime()
    r = parse(make_raw("close"), make_metadata("flagged"), runtime)
    assert r.outcome is ParseResultState.PARSED
    fragment = _action_fragment(r)
    assert fragment.value.name == "CLOSE"
    flag_evidence = [
        e
        for e in fragment.evidence
        if isinstance(e, MatchEvidence) and e.kind == "action_flags"
    ]
    assert len(flag_evidence) == 1
    assert flag_evidence[0].fields == (("origin", "explicit"), ("close_full", True))


def test_action_flags_are_deterministic_across_parses() -> None:
    first = parse(
        make_raw("REMOVE SL"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    second = parse(
        make_raw("REMOVE SL"),
        make_metadata("provider_001"),
        make_runtime("provider_001"),
    )
    assert first.ir == second.ir
