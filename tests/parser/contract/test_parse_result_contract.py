"""Parse-result single-outcome ownership (design §13.3).

``ParseResult.outcome`` is the SINGLE authoritative owner of the parse outcome;
``CanonicalParserIR`` carries no outcome field. This is a purely STRUCTURAL
contract: the derived-outcome helper ``derive_outcome(ir)`` and the §14 decision
procedure are Phase 3+ engine behaviour and are intentionally NOT exercised here.
"""

from __future__ import annotations

import pytest

from packages.parser import (
    CanonicalParserIR,
    ParseResult,
)
from packages.parser.enums import ParseResultState


def _ir(**overrides: object) -> CanonicalParserIR:
    defaults: dict[str, object] = {
        "candidates": (),
        "unresolved_fields": (),
        "fragments": (),
        "conflicts": (),
        "ambiguities": (),
        "evidence": (),
        "normalization_decisions": (),
        "conditions": (),
        "provider_id": "provider_alpha",
        "parser_version": "0.1",
    }
    defaults.update(overrides)
    return CanonicalParserIR(**defaults)  # type: ignore[arg-type]


def test_canonical_parser_ir_has_no_outcome_field() -> None:
    field_names = {f.name for f in CanonicalParserIR.__dataclass_fields__.values()}
    assert "outcome" not in field_names


def test_parse_result_outcome_is_the_single_owner() -> None:
    """The outcome lives ONLY on ParseResult, never on the IR."""
    ir = _ir()
    result = ParseResult(outcome=ParseResultState.PARSED, ir=ir)
    assert result.ir is ir
    assert result.outcome == ParseResultState.PARSED


def test_parse_result_holds_entire_closed_outcome_set() -> None:
    """The six states are a closed set; each is representable by the owner."""
    ir = _ir()
    for state in ParseResultState:
        assert ParseResult(outcome=state, ir=ir).outcome == state


def test_parse_result_rejects_non_enum_outcome() -> None:
    with pytest.raises(TypeError):
        ParseResult(outcome="PARSED", ir=_ir())  # type: ignore[arg-type]


def test_parse_result_rejects_non_ir() -> None:
    with pytest.raises(TypeError):
        ParseResult(outcome=ParseResultState.PARSED, ir=object())  # type: ignore[arg-type]
