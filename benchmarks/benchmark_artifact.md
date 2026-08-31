# Phase 1 Step 9 Benchmark Artifact

Environment:
- Python: 3.14.4 (main, Apr 8 2026, 04:02:31) [GCC 15.2.0]
- OS: Linux 7.0.0-30-generic (x86_64)
- CPU info: 12 cores
- Benchmark tool: Python standard-library time.perf_counter
- Timer resolution: perf_counter (high-resolution, monotonic)
- Warmup: 100 iterations per operation before measurement
- Iterations per measurement: 5000 (3000 for fingerprint_large due to size)
- Repeats: 5
- Date/time: generated during Step 9 execution session

Methodology:
- No production code modified.
- No new dependencies added.
- Setup time separated from measurement time (execution inside loop only).
- Statistical reporting: mean, median, min, max, standard deviation.
- Throughput computed as 1 / mean.
- Memory measurement: not performed (sys.getsizeof would be misleading for frozen nested objects; no process-level measurement made). Reported as: NOT MEASURED (would require deeper profiling framework; deferred to future profiling phase).
- GC: not manipulated (realistic Python behavior preserved).

Fixtures:
- A. MINIMAL_SIGNAL (smallest valid canonical signal)
- B. NORMAL_SIGNAL (full representative signal with SL, multiple TP, entry price)
- C. LARGE_SNAPSHOT (51 Price objects in tuple snapshot)
- D. NESTED_SNAPSHOT (deep nested tuple with Price objects)
- E. INSTRUCTIONS_E (12 instruction types, same identity)
- F. REVISION_CHAIN_F (5 linked revisions, same logical identity)
- SNAPSHOTS_SMALL (1 Price pair), MEDIUM (20), LARGE (100)

Results:
- Canonical validation (minimal): ~41,210 ops/sec (mean 24.3 µs)
- Normalization + fingerprint (small): ~48,384 ops/sec (mean 20.7 µs)
- Normalization + fingerprint (medium 20 entries): ~17,225 ops/sec (mean 58.1 µs)
- Normalization + fingerprint (large 100 entries): ~4,921 ops/sec (mean 203 µs)
- Normalization + fingerprint (deep nested): ~20,130 ops/sec (mean 49.7 µs)
- Signal construction (minimal): ~98,853 ops/sec (mean 10.1 µs)
- Signal construction (normal/full): ~78,835 ops/sec (mean 12.7 µs)
- SignalInstruction (minimal payload): ~35,683 ops/sec (mean 28.0 µs)
- SignalEvent (minimal): ~34,428 ops/sec (mean 29.0 µs)
- SignalRevision (minimal): ~18,211 ops/sec (mean 54.9 µs)
- Multi-instruction (reference first of 12): ~92,656 ops/sec
- Revision chain (reference first of 5): ~87,519 ops/sec

Fingerprint scaling:
- Small (1 pair): ~20.7 µs
- Medium (20 pairs): ~58.1 µs (~2.8x larger for 20x data — sub-linear growth)
- Large (100 pairs): ~203 µs (~9.8x larger for 100x data — sub-linear growth)
- Deep nested: ~49.7 µs (similar to medium; nesting depth does not dominate)

Bottleneck analysis:
- Measured bottleneck: None identified at current scale. Revision construction is the slowest individual operation (~55 µs), which is expected due to fingerprint computation and structural invariant delegation. Signal construction is fastest (~10–13 µs). Fingerprint scaling is sub-linear with snapshot size, suggesting SHA-256 overhead grows slowly relative to data size.
- Potential bottleneck: If canonical snapshots grow to thousands of fields, fingerprint computation could become noticeable. Not a current bottleneck.
- Insignificant costs: Deep nested tuple validation; instruction/event payload creation; identity object creation.
- Areas requiring future profiling: Large-scale replay/reconstruction (when implemented); multi-message parser ingestion path (future phase); database persistence overhead (future phase).

Correctness confirmation:
- Benchmark fixtures reuse existing valid domain objects (SignalIdentity, Price, PriceRange, Instrument, Signal).
- No domain semantics altered by instrumentation.
- Benchmark artifact saved to this file; results reproducible with same fixtures.

Dependency status:
- No external benchmark dependencies added.
- Standard library only (time, statistics, sys, datetime, decimal, uuid).

Note:
This is a microbenchmark baseline, not a production throughput guarantee.
Real-system throughput depends on adapter/parser overhead (deferred),
broker/network latency (deferred), and database/Redis persistence (deferred).
Microbenchmark results demonstrate the core domain is low-cost and suitable
as a contract layer; optimization is not currently required.
