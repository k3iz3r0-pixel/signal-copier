# Benchmarks — Phase 1 / Step 9

Performance baseline for the **existing** Phase 1 Signal Core.

This directory exists only to **measure** performance.

It does **not** modify production code and does **not** add runtime
dependencies to the project.

## Scope (per approved Step 9 instruction)

- canonical value validation
- canonical normalization
- `canonical_fingerprint`
- `Signal` construction
- `SignalInstruction` construction
- `SignalRevision` construction
- `SignalEvent` construction
- integrated identity → signal → instruction → revision → event

Out of scope (must NOT be benchmarked here):

- parser, provider adapters, broker adapters, execution, strategy,
  risk, database, Redis, replay, backtesting, analytics, AI,
  Telegram, Discord.

## Methodology

- **Standard library only.** No third-party benchmark libraries.
- No caches, no memoization, no multiprocessing, no async.
- High-resolution timer: `time.perf_counter_ns()`.
- Each measurement: warm-up runs (default 200, **excluded** from the
  measured sample) + measured iterations (default 5 000).
- Reported statistics: mean, median, p95, p99, min, max, throughput
  (ops/sec from mean).
- Setup time (fixture construction) is performed **outside** the
  timed loop and is therefore not included in the measurement.
- GC is **not** disabled or manipulated; reported as-is in the
  environment block.

## Fixtures

Defined in `benchmarks/fixtures.py`:

| Fixture | Purpose |
|---|---|
| `A_MINIMAL_SIGNAL` | lower-bound construction cost |
| `B_NORMAL_SIGNAL` | typical-signal construction cost |
| `C_LARGE_SIGNAL` | upper-bound single-signal construction cost |
| `D_NESTED_SNAPSHOT` | canonical_fingerprint cost on nested structures |
| `E_MULTI_INSTRUCTION` | SignalInstruction cost; instruction fan-out |
| `F_REVISION_CHAIN` | revision chain construction; chain link integrity |

## How to run

```bash
PYTHONPATH=. python benchmarks/run_benchmarks.py
# or with custom counts:
PYTHONPATH=. python benchmarks/run_benchmarks.py --iterations=1000 --warmups=50
```

Artifacts:

- `benchmarks/results/benchmark_report.json` (machine-readable)
- `benchmarks/results/benchmark_summary.md` (human-readable)

## Statistical quality

- A single run is **not** a guarantee. Variance is preserved in the
  per-iteration min/max; p95/p99 are reported.
- Cross-hardware comparisons require qualification. Do not present a
  number from this machine as a general property of the production
  codebase.