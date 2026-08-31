#!/usr/bin/env python3
"""Phase 1 Step 9 benchmark suite — standard library only, reproducible.

This script measures domain construction and fingerprint performance
without altering production behavior. No dependencies added.
"""
from __future__ import annotations

import statistics
import sys
import time

sys.path.insert(0, "/home/keizero/Desktop/Projects /signal-copier")

from benchmarks.benchmark_fixtures import (
    MINIMAL_SIGNAL,
    NORMAL_SIGNAL,
    LARGE_SNAPSHOT,
    NESTED_SNAPSHOT,
    INSTRUCTIONS_E,
    REVISION_CHAIN_F,
    SNAPSHOTS_SMALL,
    SNAPSHOTS_MEDIUM,
    SNAPSHOTS_LARGE,
)

from packages.signal_core.domain import (
    Signal,
    SignalEvent,
    SignalIdentity,
    SignalInstruction,
    SignalRevision,
    canonical_fingerprint,
    _validate_canonical_value,
)
from packages.signal_core.enums import EventType, InstructionType
from packages.signal_core.value_objects import Price, ProviderSource, PriceRange, Instrument
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4


def run_timer(name, setup_str, stmt_str, iterations=5000, repeats=5):
    # Use time.perf_counter for high-resolution measurement
    import time
    results = []
    for _ in range(repeats):
        # Warmup
        t0 = time.perf_counter()
        for _ in range(100):
            exec(stmt_str, globals())
        # Actual measurement
        start = time.perf_counter()
        for _ in range(iterations):
            exec(stmt_str, globals())
        end = time.perf_counter()
        results.append((end - start) / iterations)
    return {
        "name": name,
        "mean_s": statistics.mean(results),
        "median_s": statistics.median(results),
        "min_s": min(results),
        "max_s": max(results),
        "stdev_s": statistics.stdev(results) if len(results) > 1 else 0.0,
        "iterations": iterations,
        "repeats": repeats,
    }


def main():
    identity_obj = MINIMAL_SIGNAL.identity
    instrument_obj = MINIMAL_SIGNAL.instrument

    results = []

    # 1. Canonical value validation (minimal snapshot value)
    results.append(run_timer(
        "validate_canonical_value_minimal",
        "from packages.signal_core.domain import _validate_canonical_value",
        "_validate_canonical_value(Price(value=Decimal('1.1')))",
        iterations=5000, repeats=5,
    ))

    # 2. Normalization (minimal snapshot)
    results.append(run_timer(
        "normalize_fingerprint_minimal",
        "from benchmarks.benchmark_fixtures import MINIMAL_SIGNAL; from packages.signal_core.domain import canonical_fingerprint",
        "canonical_fingerprint((('instrument', MINIMAL_SIGNAL.instrument),))",
        iterations=5000, repeats=5,
    ))

    # 3. Signal construction (minimal)
    results.append(run_timer(
        "signal_construction_minimal",
        "from benchmarks.benchmark_fixtures import MINIMAL_SIGNAL",
        "MINIMAL_SIGNAL",
        iterations=5000, repeats=5,
    ))

    # 4. Signal construction (normal)
    results.append(run_timer(
        "signal_construction_normal",
        "from benchmarks.benchmark_fixtures import NORMAL_SIGNAL",
        "NORMAL_SIGNAL",
        iterations=5000, repeats=5,
    ))

    # 5. SignalInstruction (minimal payload)
    results.append(run_timer(
        "instruction_construction_minimal",
        "from benchmarks.benchmark_fixtures import MINIMAL_SIGNAL",
        "SignalInstruction(instruction_type=InstructionType.MODIFY, signal_identity=MINIMAL_SIGNAL.identity, created_at_utc=MINIMAL_SIGNAL.created_at_utc)",
        iterations=5000, repeats=5,
    ))

    # 6. SignalRevision (minimal)
    results.append(run_timer(
        "revision_construction_minimal",
        "from benchmarks.benchmark_fixtures import MINIMAL_SIGNAL; from packages.signal_core.domain import SignalRevision",
        "SignalRevision(revision_id=uuid4(), logical_signal_id=MINIMAL_SIGNAL.identity.logical_signal_id, revision_number=1, previous_revision_id=None, canonical_snapshot=(), fingerprint='ignored', created_at_utc=MINIMAL_SIGNAL.created_at_utc)",
        iterations=5000, repeats=5,
    ))

    # 7. SignalEvent (minimal)
    results.append(run_timer(
        "event_construction_minimal",
        "from benchmarks.benchmark_fixtures import MINIMAL_SIGNAL",
        "SignalEvent(event_id=MINIMAL_SIGNAL.identity.logical_signal_id, signal_identity=MINIMAL_SIGNAL.identity, event_type=EventType.CREATED, timestamp_utc=MINIMAL_SIGNAL.created_at_utc)",
        iterations=5000, repeats=5,
    ))

    # 8. Canonical fingerprint small
    results.append(run_timer(
        "fingerprint_small",
        "from benchmarks.benchmark_fixtures import SNAPSHOTS_SMALL; from packages.signal_core.domain import canonical_fingerprint",
        "canonical_fingerprint(SNAPSHOTS_SMALL)",
        iterations=5000, repeats=5,
    ))

    # 9. Canonical fingerprint medium
    results.append(run_timer(
        "fingerprint_medium",
        "from benchmarks.benchmark_fixtures import SNAPSHOTS_MEDIUM; from packages.signal_core.domain import canonical_fingerprint",
        "canonical_fingerprint(SNAPSHOTS_MEDIUM)",
        iterations=5000, repeats=5,
    ))

    # 10. Canonical fingerprint large
    results.append(run_timer(
        "fingerprint_large",
        "from benchmarks.benchmark_fixtures import SNAPSHOTS_LARGE; from packages.signal_core.domain import canonical_fingerprint",
        "canonical_fingerprint(SNAPSHOTS_LARGE)",
        iterations=3000, repeats=5,
    ))

    # 11. Nested deep snapshot fingerprint
    results.append(run_timer(
        "fingerprint_nested_deep",
        "from benchmarks.benchmark_fixtures import NESTED_SNAPSHOT; from packages.signal_core.domain import canonical_fingerprint",
        "canonical_fingerprint((('nested', NESTED_SNAPSHOT[0][1]),))",
        iterations=5000, repeats=5,
    ))

    # 12. Multi-instruction construction
    results.append(run_timer(
        "multi_instruction",
        "from benchmarks.benchmark_fixtures import INSTRUCTIONS_E",
        "INSTRUCTIONS_E[0]",
        iterations=5000, repeats=5,
    ))

    # 13. Revision chain (5 revisions)
    results.append(run_timer(
        "revision_chain_5",
        "from benchmarks.benchmark_fixtures import REVISION_CHAIN_F",
        "REVISION_CHAIN_F[0]",
        iterations=5000, repeats=5,
    ))

    # Print results
    for r in results:
        print(f"OPERATION: {r['name']}")
        print(f"  iterations: {r['iterations']} | repeats: {r['repeats']}")
        print(f"  mean: {r['mean_s']:.9f}s  median: {r['median_s']:.9f}s")
        print(f"  min: {r['min_s']:.9f}s  max: {r['max_s']:.9f}s")
        print(f"  stdev: {r['stdev_s']:.9f}s")
        if r['mean_s'] > 0:
            print(f"  throughput: {1.0 / r['mean_s']:,.0f} ops/sec")
        print()


if __name__ == "__main__":
    main()
