"""Standard-library-only benchmark runner for Phase 1 — Step 9.

This module:
    - measures individual operations (canonical validation,
      normalization, fingerprint, Signal/Instruction/Revision/Event
      construction),
    - measures an integrated identity -> signal -> instruction ->
      revision -> event operation,
    - measures fingerprint cost against snapshot size,
    - reports mean / median / p95 / p99 / min / max and throughput,
    - records environment metadata,
    - writes a reproducible JSON artifact under benchmarks/results/.

It does NOT modify production code.

It does NOT introduce caches, memoization, multiprocessing, or async.
"""

from __future__ import annotations

import gc
import json
import platform
import statistics
import sys
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from os import cpu_count as os_cpu_count
from pathlib import Path
from typing import Any
from uuid import UUID

from benchmarks.fixtures import (
    FIXED_LOGICAL_ID,
    FIXED_REVISION_ID_1,
    FIXED_REVISION_ID_2,
    FIXED_TS,
    FIXTURES,
    FixtureSpec,
    build_canonical_snapshot,
    build_event,
    build_fingerprint_scaling_points,
    build_identity,
    build_instruction,
    build_revision_chain,
    build_signal,
)
from packages.signal_core.domain import (
    Signal,
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    _normalize_for_fingerprint,
    _validate_canonical_value,
    canonical_fingerprint,
)
from packages.signal_core.enums import EventType

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"

DEFAULT_ITERATIONS = 5_000
DEFAULT_WARMUPS = 200
FINGERPRINT_SCALING_ITERATIONS = 5_000
FINGERPRINT_SCALING_WARMUPS = 200


# ----------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkResult:
    """One benchmark measurement row."""

    operation: str
    fixture: str
    iterations: int
    warmups: int
    mean_seconds: float
    median_seconds: float
    p95_seconds: float
    p99_seconds: float
    min_seconds: float
    max_seconds: float
    throughput_ops_per_sec: float
    snapshot_fields: int
    snapshot_total_items: int
    notes: str = ""


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Return the linear-interpolated percentile of ``sorted_values``."""

    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def measure_operation(
    operation: Callable[[], Any],
    *,
    iterations: int,
    warmups: int,
) -> tuple[list[float], float]:
    """Run ``operation`` ``warmups + iterations`` times.

    Returns (per-iteration_seconds, total_elapsed_seconds).
    """

    for _ in range(warmups):
        operation()

    samples: list[float] = []
    start_total = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        operation()
        t1 = time.perf_counter_ns()
        samples.append((t1 - t0) / 1e9)
    end_total = time.perf_counter()
    return samples, end_total - start_total


def _summarize(
    operation: str,
    fixture: str,
    iterations: int,
    warmups: int,
    samples: list[float],
    snapshot_fields: int,
    snapshot_total_items: int,
    notes: str = "",
) -> BenchmarkResult:
    sorted_samples = sorted(samples)
    mean = statistics.fmean(samples)
    median = statistics.median(samples)
    p95 = _percentile(sorted_samples, 95.0)
    p99 = _percentile(sorted_samples, 99.0)
    throughput = (1.0 / mean) if mean > 0 else float("inf")
    return BenchmarkResult(
        operation=operation,
        fixture=fixture,
        iterations=iterations,
        warmups=warmups,
        mean_seconds=mean,
        median_seconds=median,
        p95_seconds=p95,
        p99_seconds=p99,
        min_seconds=sorted_samples[0],
        max_seconds=sorted_samples[-1],
        throughput_ops_per_sec=throughput,
        snapshot_fields=snapshot_fields,
        snapshot_total_items=snapshot_total_items,
        notes=notes,
    )


# ----------------------------------------------------------------------
# Operation definitions
# ----------------------------------------------------------------------


def _op_canonical_validation(
    snapshot: tuple[tuple[str, Any], ...],
) -> Callable[[], None]:
    def _run() -> None:
        for k, v in snapshot:
            if not isinstance(k, str):
                raise TypeError("key must be str")
            _validate_canonical_value(v, f"['{k}']")

    return _run


def _op_canonical_normalization(
    snapshot: tuple[tuple[str, Any], ...],
) -> Callable[[], None]:
    def _run() -> None:
        normalized = tuple(
            sorted((str(k), _normalize_for_fingerprint(v)) for k, v in snapshot)
        )
        if len(normalized) < 0:  # pragma: no cover
            raise RuntimeError("unreachable")

    return _run


def _op_canonical_fingerprint(
    snapshot: tuple[tuple[str, Any], ...],
) -> Callable[[], str]:
    def _run() -> str:
        return canonical_fingerprint(snapshot)

    return _run


def _op_signal_construction(fixture: str) -> Callable[[], Signal]:
    def _run() -> Signal:
        return build_signal(fixture)

    return _run


def _op_instruction_construction(
    fixture: str, index: int = 0
) -> Callable[[], SignalInstruction]:
    def _run() -> SignalInstruction:
        return build_instruction(fixture, index)

    return _run


def _op_revision_construction(fixture: str) -> Callable[[], SignalRevision]:
    def _run() -> SignalRevision:
        snapshot = build_canonical_snapshot(fixture)
        return SignalRevision(
            revision_id=FIXED_REVISION_ID_1,
            logical_signal_id=FIXED_LOGICAL_ID,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=FIXED_TS,
        )

    return _run


def _op_event_construction(fixture: str) -> Callable[[], SignalEvent]:
    def _run() -> SignalEvent:
        return build_event(fixture)

    return _run


def _op_integrated_pipeline(
    fixture: str,
) -> Callable[
    [], tuple[SignalIdentity, Signal, SignalInstruction, SignalRevision, SignalEvent]
]:
    def _run() -> tuple[
        SignalIdentity, Signal, SignalInstruction, SignalRevision, SignalEvent
    ]:
        identity = build_identity()
        signal = build_signal(fixture)
        instruction = build_instruction(fixture, 0)
        snapshot = build_canonical_snapshot(fixture)
        revision = SignalRevision(
            revision_id=FIXED_REVISION_ID_1,
            logical_signal_id=FIXED_LOGICAL_ID,
            revision_number=1,
            previous_revision_id=None,
            canonical_snapshot=snapshot,
            fingerprint="ignored",
            created_at_utc=FIXED_TS,
        )
        event = SignalEvent(
            event_id=UUID("55555555-5555-4555-8555-555555555555"),
            signal_identity=identity,
            event_type=EventType.REVISED,
            timestamp_utc=FIXED_TS,
            previous_revision_id=revision.revision_id,
            new_revision_id=FIXED_REVISION_ID_2,
        )
        return identity, signal, instruction, revision, event

    return _run


# ----------------------------------------------------------------------
# Memory measurement
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryResult:
    """Approximate memory footprint of representative objects."""

    object_name: str
    shallow_bytes: int
    deep_current_bytes: int | None
    deep_peak_bytes: int | None
    methodology: str


def measure_memory_shallow(obj: Any, name: str) -> MemoryResult:
    """Measure ``sys.getsizeof`` of ``obj`` (shallow only)."""

    return MemoryResult(
        object_name=name,
        shallow_bytes=sys.getsizeof(obj),
        deep_current_bytes=None,
        deep_peak_bytes=None,
        methodology="sys.getsizeof (shallow only; excludes nested members)",
    )


def measure_memory_deep(obj: Any, name: str) -> MemoryResult:
    """Measure approximate deep memory using ``tracemalloc`` around re-construction."""

    gc.collect()
    tracemalloc.start()
    try:
        if name.startswith("Signal[B_") or name == "Signal":
            _ = build_signal("B_NORMAL_SIGNAL")
        elif name.startswith("SignalRevision["):
            fixture_name = name[len("SignalRevision[") : -1]
            _ = SignalRevision(
                revision_id=FIXED_REVISION_ID_1,
                logical_signal_id=FIXED_LOGICAL_ID,
                revision_number=1,
                previous_revision_id=None,
                canonical_snapshot=build_canonical_snapshot(fixture_name),
                fingerprint="ignored",
                created_at_utc=FIXED_TS,
            )
        elif name.startswith("SignalInstruction["):
            fixture_name = name[len("SignalInstruction[") : -1]
            _ = build_instruction(fixture_name, 0)
        elif name.startswith("SignalEvent["):
            fixture_name = name[len("SignalEvent[") : -1]
            _ = build_event(fixture_name)
        else:
            _ = obj
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return MemoryResult(
        object_name=name,
        shallow_bytes=sys.getsizeof(obj),
        deep_current_bytes=current,
        deep_peak_bytes=peak,
        methodology="tracemalloc around single construction call",
    )


# ----------------------------------------------------------------------
# Run-all orchestrator
# ----------------------------------------------------------------------


@dataclass
class BenchmarkReport:
    environment: dict[str, Any] = field(default_factory=dict)
    benchmark_tool: str = "stdlib time.perf_counter_ns"
    timer: str = "time.perf_counter_ns / time.perf_counter"
    iterations_default: int = 0
    warmups_default: int = 0
    operations: list[BenchmarkResult] = field(default_factory=list)
    fingerprint_scaling: list[BenchmarkResult] = field(default_factory=list)
    memory: list[MemoryResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _environment() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count_logical": os_cpu_count(),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "gc_enabled": gc.isenabled(),
    }


def run_all_benchmarks(
    *,
    iterations: int = DEFAULT_ITERATIONS,
    warmups: int = DEFAULT_WARMUPS,
    include_memory: bool = True,
) -> BenchmarkReport:
    report = BenchmarkReport(
        environment=_environment(),
        iterations_default=iterations,
        warmups_default=warmups,
        notes=[
            "stdlib-only; no caches, no memoization, no multiprocessing.",
            (
                "Setup time (fixture construction outside the timed loop) "
                "is explicitly excluded from the measured iteration."
            ),
            "Throughput is operations per second derived from mean_seconds.",
            (
                "Results are reproducible across runs with the same Python "
                "build and OS load; cross-hardware comparisons require "
                "qualification (see report)."
            ),
        ],
    )

    for fixture_name in FIXTURES:
        spec: FixtureSpec = FIXTURES[fixture_name]
        snapshot = build_canonical_snapshot(fixture_name)

        op: Callable[[], Any] = _op_canonical_validation(snapshot)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="canonical_validation",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        op = _op_canonical_normalization(snapshot)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="canonical_normalization",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        op = _op_canonical_fingerprint(snapshot)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="canonical_fingerprint",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        op = _op_signal_construction(fixture_name)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="signal_construction",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        op = _op_instruction_construction(fixture_name, 0)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="instruction_construction",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        op = _op_revision_construction(fixture_name)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="revision_construction",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        op = _op_event_construction(fixture_name)
        samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
        report.operations.append(
            _summarize(
                operation="event_construction",
                fixture=fixture_name,
                iterations=iterations,
                warmups=warmups,
                samples=samples,
                snapshot_fields=spec.canonical_size_fields,
                snapshot_total_items=spec.canonical_size_total_items,
            )
        )

        if fixture_name == "B_NORMAL_SIGNAL":
            op = _op_integrated_pipeline(fixture_name)
            samples, _ = measure_operation(op, iterations=iterations, warmups=warmups)
            report.operations.append(
                _summarize(
                    operation="integrated_pipeline",
                    fixture=fixture_name,
                    iterations=iterations,
                    warmups=warmups,
                    samples=samples,
                    snapshot_fields=spec.canonical_size_fields,
                    snapshot_total_items=spec.canonical_size_total_items,
                    notes=("identity->signal->instruction->revision->event"),
                )
            )

    for sp in build_fingerprint_scaling_points():
        op = _op_canonical_fingerprint(sp.snapshot)
        samples, _ = measure_operation(
            op,
            iterations=FINGERPRINT_SCALING_ITERATIONS,
            warmups=FINGERPRINT_SCALING_WARMUPS,
        )
        snapshot_fields = len(sp.snapshot)
        snapshot_total = _count_total_items(sp.snapshot)
        report.fingerprint_scaling.append(
            _summarize(
                operation="canonical_fingerprint_scaling",
                fixture=sp.label,
                iterations=FINGERPRINT_SCALING_ITERATIONS,
                warmups=FINGERPRINT_SCALING_WARMUPS,
                samples=samples,
                snapshot_fields=snapshot_fields,
                snapshot_total_items=snapshot_total,
                notes=f"scaling point label={sp.label}",
            )
        )

    if include_memory:
        try:
            sig = build_signal("B_NORMAL_SIGNAL")
            rev_snapshot = build_canonical_snapshot("B_NORMAL_SIGNAL")
            rev = SignalRevision(
                revision_id=FIXED_REVISION_ID_1,
                logical_signal_id=FIXED_LOGICAL_ID,
                revision_number=1,
                previous_revision_id=None,
                canonical_snapshot=rev_snapshot,
                fingerprint="ignored",
                created_at_utc=FIXED_TS,
            )
            inst = build_instruction("E_MULTI_INSTRUCTION", 0)
            evt = build_event("B_NORMAL_SIGNAL")
            chain = build_revision_chain("F_REVISION_CHAIN")

            report.memory.append(measure_memory_shallow(sig, "Signal[B_NORMAL_SIGNAL]"))
            report.memory.append(
                measure_memory_shallow(rev, "SignalRevision[B_NORMAL_SIGNAL]")
            )
            report.memory.append(
                measure_memory_shallow(inst, "SignalInstruction[E_MULTI_INSTRUCTION]")
            )
            report.memory.append(
                measure_memory_shallow(evt, "SignalEvent[B_NORMAL_SIGNAL]")
            )

            report.memory.append(measure_memory_deep(sig, "Signal[B_NORMAL_SIGNAL]"))
            report.memory.append(
                measure_memory_deep(rev, "SignalRevision[B_NORMAL_SIGNAL]")
            )
            report.memory.append(
                measure_memory_deep(inst, "SignalInstruction[E_MULTI_INSTRUCTION]")
            )
            report.memory.append(
                measure_memory_deep(evt, "SignalEvent[B_NORMAL_SIGNAL]")
            )

            report.memory.append(
                MemoryResult(
                    object_name="RevisionChain[F_REVISION_CHAIN]",
                    shallow_bytes=sys.getsizeof(chain),
                    deep_current_bytes=None,
                    deep_peak_bytes=None,
                    methodology="list of 3 SignalRevision; shallow list size only",
                )
            )
        except (TypeError, ValueError, AttributeError) as e:  # benchmark safety net
            report.notes.append(f"Memory measurement failed: {e!r}")

    return report


def _count_total_items(snapshot: tuple[tuple[str, Any], ...]) -> int:
    total = 0
    for _k, v in snapshot:
        if isinstance(v, tuple):
            total += 1 + _count_total_items(tuple((str(i), x) for i, x in enumerate(v)))
        else:
            total += 1
    return total


# ----------------------------------------------------------------------
# Reporting / artifact writing
# ----------------------------------------------------------------------


def write_report(report: BenchmarkReport, path: Path) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "environment": report.environment,
        "benchmark_tool": report.benchmark_tool,
        "timer": report.timer,
        "iterations_default": report.iterations_default,
        "warmups_default": report.warmups_default,
        "notes": report.notes,
        "operations": [asdict(r) for r in report.operations],
        "fingerprint_scaling": [asdict(r) for r in report.fingerprint_scaling],
        "memory": [asdict(m) for m in report.memory],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def write_markdown_summary(report: BenchmarkReport, path: Path) -> None:
    lines: list[str] = []
    env = report.environment
    lines.append("# Phase 1 — Step 9 Performance Baseline")
    lines.append("")
    lines.append("## Environment")
    lines.append("")
    lines.append(f"- Python: {env.get('python_version')}")
    lines.append(f"- Python implementation: {env.get('python_implementation')}")
    lines.append(f"- Platform: {env.get('platform')}")
    lines.append(f"- Machine: {env.get('machine')}")
    lines.append(f"- Processor: {env.get('processor')}")
    lines.append(f"- Logical CPU count: {env.get('cpu_count_logical')}")
    lines.append(f"- GC enabled: {env.get('gc_enabled')}")
    lines.append(f"- Timestamp (UTC): {env.get('timestamp_utc')}")
    lines.append(f"- Benchmark tool: {report.benchmark_tool}")
    lines.append(f"- Timer: {report.timer}")
    lines.append(f"- Iterations (default): {report.iterations_default}")
    lines.append(f"- Warmups (default): {report.warmups_default}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for n in report.notes:
        lines.append(f"- {n}")
    lines.append("")

    lines.append("## Operations")
    lines.append("")
    lines.append(
        "| Operation | Fixture | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in report.operations:
        lines.append(
            f"| {r.operation} | {r.fixture} | {r.iterations} | "
            f"{r.mean_seconds:.9f} | {r.median_seconds:.9f} | "
            f"{r.p95_seconds:.9f} | {r.p99_seconds:.9f} | "
            f"{r.min_seconds:.9f} | {r.max_seconds:.9f} | "
            f"{r.throughput_ops_per_sec:.1f} | "
            f"{r.snapshot_fields} | {r.snapshot_total_items} |"
        )
    lines.append("")

    lines.append("## Fingerprint scaling")
    lines.append("")
    lines.append(
        "| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in report.fingerprint_scaling:
        lines.append(
            f"| {r.fixture} | {r.iterations} | "
            f"{r.mean_seconds:.9f} | {r.median_seconds:.9f} | "
            f"{r.p95_seconds:.9f} | {r.p99_seconds:.9f} | "
            f"{r.min_seconds:.9f} | {r.max_seconds:.9f} | "
            f"{r.throughput_ops_per_sec:.1f} | "
            f"{r.snapshot_fields} | {r.snapshot_total_items} |"
        )
    lines.append("")

    lines.append("## Memory")
    lines.append("")
    lines.append(
        "| Object | Shallow (bytes) | Deep current (bytes) | Deep peak (bytes) | Methodology |"
    )
    lines.append("|---|---:|---:|---:|---|")
    for m in report.memory:
        dc = "n/a" if m.deep_current_bytes is None else f"{m.deep_current_bytes}"
        dp = "n/a" if m.deep_peak_bytes is None else f"{m.deep_peak_bytes}"
        lines.append(
            f"| {m.object_name} | {m.shallow_bytes} | {dc} | {dp} | {m.methodology} |"
        )
    lines.append("")

    path.write_text("\n".join(lines))


__all__ = [
    "DEFAULT_ITERATIONS",
    "DEFAULT_WARMUPS",
    "FINGERPRINT_SCALING_ITERATIONS",
    "FINGERPRINT_SCALING_WARMUPS",
    "REPO_ROOT",
    "RESULTS_DIR",
    "BenchmarkReport",
    "BenchmarkResult",
    "MemoryResult",
    "measure_memory_deep",
    "measure_memory_shallow",
    "measure_operation",
    "run_all_benchmarks",
    "write_markdown_summary",
    "write_report",
]
