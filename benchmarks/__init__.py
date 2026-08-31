"""Phase 1 — Step 9 Performance Baseline (benchmarking only).

This package measures, it does not modify production code.

Scope (benchmark only):
    - canonical value validation
    - canonical normalization
    - canonical_fingerprint
    - Signal construction
    - SignalInstruction construction
    - SignalRevision construction
    - SignalEvent construction
    - integrated identity -> signal -> instruction -> revision -> event composition

Out of scope (must NOT be benchmarked here):
    - parser, provider adapters, broker adapters, execution,
      strategy, risk, database, Redis, replay, backtesting,
      analytics, AI, Telegram, Discord.

Constraints (from Step 9 instruction):
    - Standard library only.
    - No caches, no memoization, no multiprocessing, no async.
    - Deterministic inputs.
    - Separate setup time from measured operation time.
    - Statistical rigor: mean, median, p95, p99, min, max.
    - Reproducible artifact written under benchmarks/results/.
"""
