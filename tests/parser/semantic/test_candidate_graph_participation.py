"""CandidateGraph participation regression tests (Phase 2B.1 remediation).

The Phase 2B audit found that CandidateGraph was populated but the
resolver operated only on RuleMatch bindings, reconstructing candidates
and silently discarding those that "appeared second" (second instrument,
second direction, second SL anchor, non-selected occurrence sites).

After the remediation:

- every authorized rule site is bound as a Candidate; the sites selected
  by the rule's ``occurrence`` become RuleMatch bindings, the rest are
  merged into the CandidateGraph as alternatives (§6.1);
- the resolver CONSUMES the graph: merged per-slot candidates are
  classified per §6.2 (duplicate / conflicting / ambiguous) so competing
  candidates survive until resolution;
- identical-value alternatives still collapse (no false conflicts).
"""

from __future__ import annotations

from decimal import Decimal

from packages.parser import parse
from packages.parser.enums import (
    CandidateSlot,
    ConflictKind,
    ParseResultState,
)
from packages.parser.pipeline import (
    _merge_candidate_graphs,
    evaluate_rules,
    extract_candidates,
    normalize,
    resolve_candidates,
    tokenize,
)
from packages.parser.types import SourceSpan
from packages.signal_core.value_objects import Price
from tests.parser._helpers import make_metadata, make_raw, make_runtime

PROVIDER = "provider_001"


def _go(text: str, provider: str = PROVIDER):
    return parse(make_raw(text), make_metadata(provider), make_runtime(provider))


def _stages(text: str, provider: str = PROVIDER):
    rt = make_runtime(provider)
    norm = normalize(text, rt)
    positioned, _ = tokenize(norm, rt)
    extract_graph, _, _ = extract_candidates(positioned, rt)
    metadata = make_metadata(provider)
    matches, _violations, _unsupported, alternatives = evaluate_rules(
        positioned, norm, metadata, rt, text
    )
    graph = _merge_candidate_graphs(extract_graph, alternatives)
    return rt, norm, positioned, graph, matches, alternatives


def _graph_slot(graph, slot: CandidateSlot):
    for s, candidates in graph.by_slot:
        if s is slot:
            return list(candidates)
    return []


# ---------------------------------------------------------------------------
# Graph preservation before resolution (§5.7, §6.1)
# ---------------------------------------------------------------------------


def test_second_sl_anchor_site_is_preserved_as_alternative() -> None:
    """The non-selected occurrence site survives as a graph candidate
    instead of being silently discarded (§6.1)."""
    text = "BUY EURUSD 1.1000 SL 1.0950 SL 1.0960"
    _rt, _norm, _positioned, graph, matches, site_candidates = _stages(text)
    sl_sites = [c for c in site_candidates if c.slot is CandidateSlot.SL]
    assert {c.value for c in sl_sites} == {
        Price(Decimal("1.0950")),
        Price(Decimal("1.0960")),
    }
    # Only the FIRST site is a RuleMatch binding (occurrence=FIRST); the
    # second site exists exclusively as a graph candidate.
    bound_values = {
        c.value for m in matches for _, c in m.bindings if c.slot is CandidateSlot.SL
    }
    assert bound_values == {Price(Decimal("1.0950"))}
    # The merged graph carries BOTH SL values before resolution.
    merged_values = [c.value for c in _graph_slot(graph, CandidateSlot.SL)]
    assert Price(Decimal("1.0950")) in merged_values
    assert Price(Decimal("1.0960")) in merged_values


def test_second_instrument_site_is_preserved_in_graph() -> None:
    _rt, _norm, _positioned, graph, matches, site_candidates = _stages(
        "BUY EURUSD GBPUSD"
    )
    instrument_sites = [
        c for c in site_candidates if c.slot is CandidateSlot.INSTRUMENT
    ]
    assert {c.value for c in instrument_sites} == {"EURUSD", "GBPUSD"}
    bound_values = {
        c.value
        for m in matches
        for _, c in m.bindings
        if c.slot is CandidateSlot.INSTRUMENT
    }
    assert bound_values == {"EURUSD"}  # occurrence=FIRST
    graph_values = [c.value for c in _graph_slot(graph, CandidateSlot.INSTRUMENT)]
    assert set(graph_values) == {"EURUSD", "GBPUSD"}


# ---------------------------------------------------------------------------
# Resolver consumes the graph (§6.2)
# ---------------------------------------------------------------------------


def test_resolver_produces_conflict_only_through_the_graph() -> None:
    """Direct proof of resolver consumption: the RuleMatch bindings alone
    carry only the FIRST SL value; the conflicting second value comes
    exclusively from the CandidateGraph."""
    text = "BUY EURUSD 1.1000 SL 1.0950 SL 1.0960"
    rt, _norm, _positioned, graph, matches, _alternatives = _stages(text)

    # Resolution WITHOUT the graph: no conflict (the alternative is absent).
    only_matches = resolve_candidates(matches, None, rt)
    assert only_matches.conflicts == ()

    # Resolution WITH the graph: the second SL candidate surfaces as a
    # Conflict — the resolver consumed the graph.
    with_graph = resolve_candidates(matches, graph, rt)
    sl_conflicts = [c for c in with_graph.conflicts if c.slot is CandidateSlot.SL]
    assert len(sl_conflicts) == 1
    assert sl_conflicts[0].kind is ConflictKind.CONFLICTING
    assert {c.value for c in sl_conflicts[0].involved} == {
        Price(Decimal("1.0950")),
        Price(Decimal("1.0960")),
    }


# ---------------------------------------------------------------------------
# End-to-end conflict behaviors
# ---------------------------------------------------------------------------


def test_two_instruments_conflict_until_resolution() -> None:
    r = _go("BUY EURUSD GBPUSD")
    conflicts = [c for c in r.ir.conflicts if c.slot is CandidateSlot.INSTRUMENT]
    assert conflicts
    assert conflicts[0].kind is ConflictKind.CONFLICTING
    assert {c.value for c in conflicts[0].involved} == {"EURUSD", "GBPUSD"}
    assert r.outcome is ParseResultState.MALFORMED
    # The winner (first instrument per §6.3 order) is still emitted.
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.INSTRUMENT] == "EURUSD"


def test_two_directions_conflict_until_resolution() -> None:
    r = _go("BUY SELL")
    conflicts = [c for c in r.ir.conflicts if c.slot is CandidateSlot.DIRECTION]
    assert conflicts
    assert {c.value.name for c in conflicts[0].involved} == {"BUY", "SELL"}
    assert r.outcome is ParseResultState.MALFORMED


def test_second_sl_anchor_conflicts() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 SL 1.0960")
    conflicts = [c for c in r.ir.conflicts if c.slot is CandidateSlot.SL]
    assert conflicts
    assert {c.value for c in conflicts[0].involved} == {
        Price(Decimal("1.0950")),
        Price(Decimal("1.0960")),
    }
    assert r.outcome is ParseResultState.MALFORMED


def test_duplicate_same_value_alternatives_do_not_conflict() -> None:
    """'BUY BUY': same value, different span -> duplicate, not conflict."""
    r = _go("BUY BUY")
    assert not [c for c in r.ir.conflicts if c.slot is CandidateSlot.DIRECTION]
    assert r.outcome is ParseResultState.PARTIAL


def test_multiple_entry_candidates_survive_until_resolution() -> None:
    """Laddered entries: both values are kept as ENTRY candidates through
    resolution and the resolved fragment carries the full candidate set."""
    rt, _norm, _positioned, graph, matches, _alternatives = _stages(
        "BUY EURUSD 1.1000 1.1050 SL 1.0950"
    )
    entry_values = [c.value for c in _graph_slot(graph, CandidateSlot.ENTRY)]
    assert Price(Decimal("1.1000")) in entry_values
    assert Price(Decimal("1.1050")) in entry_values
    resolution = resolve_candidates(matches, graph, rt)
    assert resolution.entry_values == (
        Price(Decimal("1.1000")),
        Price(Decimal("1.1050")),
    )
    r = _go("BUY EURUSD 1.1000 1.1050 SL 1.0950")
    assert r.outcome is ParseResultState.PARSED
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.ENTRY] == (
        Price(Decimal("1.1000")),
        Price(Decimal("1.1050")),
    )


def test_multiple_tp_candidates_accumulate_without_conflict() -> None:
    r = _go("BUY EURUSD 1.1000 SL 1.0950 TP 1.1100 TP 1.1150")
    assert r.outcome is ParseResultState.PARSED
    assert not r.ir.conflicts
    by_slot = {f.slot: f.value for f in r.ir.fragments}
    assert by_slot[CandidateSlot.TP] == (
        Price(Decimal("1.1100")),
        Price(Decimal("1.1150")),
    )


def test_conflicting_candidates_are_not_silently_dropped_from_ir() -> None:
    """Both sides of every conflict remain reachable from the IR: in
    ir.candidates (winners + reference candidates) or in conflict.involved."""
    r = _go("BUY EURUSD 1.1000 SL 1.0950 SL 1.0960")
    involved = {c.value for conflict in r.ir.conflicts for c in conflict.involved}
    assert {Price(Decimal("1.0950")), Price(Decimal("1.0960"))} <= involved


def test_graph_slot_ordering_is_deterministic() -> None:
    """§5.7: graph candidates sorted by (span start, span end, provenance)."""
    _rt, _norm, _positioned, graph, _matches, _alternatives = _stages(
        "BUY EURUSD 1.1000 SL 1.0950 SL 1.0960"
    )
    sl = _graph_slot(graph, CandidateSlot.SL)
    keys = [(c.source_span.start, c.source_span.end, len(c.provenance)) for c in sl]
    assert keys == sorted(keys)


def test_alternative_candidate_spans_are_raw_offsets() -> None:
    text = "BUY EURUSD 1.1000 SL 1.0950 SL 1.0960"
    _rt, _norm, _positioned, _graph, _matches, site_candidates = _stages(text)
    second_sl = [
        c
        for c in site_candidates
        if c.slot is CandidateSlot.SL and c.value == Price(Decimal("1.0960"))
    ]
    assert len(second_sl) == 1
    span = second_sl[0].source_span
    assert isinstance(span, SourceSpan)
    assert text[span.start : span.end] == "1.0960"
