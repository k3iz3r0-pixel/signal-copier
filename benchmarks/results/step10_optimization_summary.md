# Step 10 - Controlled Performance Optimization Report

## STEP 9 BASELINE

Original Step 9 artifact: `benchmarks/results/step9_baseline_report.json` (immutable)
Step 10 baseline (re-measured for variance): `benchmarks/results/step10_baseline_3runs_report.json` (3 runs)

## Baseline numbers (B_NORMAL_SIGNAL, min-of-mins across 3 runs)

| op | baseline (min-of-mins) | exp3 (min-of-mins) | delta |
|---|---:|---:|---:|
| canonical_fingerprint | 1.9486e-05 | 1.3200e-05 | -32.3% |
| signal_construction | 1.0546e-05 | 1.0546e-05 | +0.0% |
| revision_construction | 3.1428e-05 | 2.3257e-05 | -26.0% |
| event_construction | 4.6800e-06 | 4.3300e-06 | -7.5% |
| integrated_pipeline | 5.0636e-05 | 4.4699e-05 | -11.7% |

## Baseline numbers (B_NORMAL_SIGNAL, median of run-medians)

| op | baseline median-of-medians | exp3 median-of-medians | delta |
|---|---:|---:|---:|
| canonical_fingerprint | 2.9054e-05 | 2.1022e-05 | -27.6% |
| signal_construction | 1.6622e-05 | 1.6622e-05 | +0.0% |
| revision_construction | 4.5327e-05 | 3.7156e-05 | -18.0% |
| event_construction | 7.7520e-06 | 7.7520e-06 | +0.0% |
| integrated_pipeline | 8.2274e-05 | 7.1029e-05 | -13.7% |

## Fingerprint scaling comparison

| label | baseline median | exp3 median | delta |
|---|---:|---:|---:|
| small | 7.9610e-06 | 6.3560e-06 | -20.2% |
| medium | 1.7565e-05 | 1.2501e-05 | -28.8% |
| large | 2.0303e-04 | 1.3556e-04 | -33.2% |
| xlarge | 7.9368e-04 | 5.4124e-04 | -31.8% |

## Final Step 10 state (single run after applying Experiment 3)

| op | final (mean) |
|---|---:|
| canonical_fingerprint | 2.3764e-05 |
| signal_construction | 1.6224e-05 |
| revision_construction | 3.3278e-05 |
| event_construction | 8.0124e-06 |
| integrated_pipeline | 7.5001e-05 |

## Memory

See `benchmarks/results/step10_final_report.json` `memory` section for shallow + tracemalloc data.

## Experiments summary

| ID | Description | Result |
|---|---|---|
| EXP1 | Remove redundant sorted() before json.dumps(sort_keys=True) | REJECTED - fingerprint regressed (+1.6%); redundant at Python level only because json.dumps re-sorts keys |
| EXP2 | Sort by `key=` lambda instead of full-tuple default sort | REJECTED - fingerprint regressed (+11.4%); lambda call cost > saved comparison cost |
| EXP3 | Combine validation + normalization into single tree traversal | ACCEPTED - canonical_fingerprint -32.3% (min-of-mins), integrated_pipeline -11.7% |
| EXP4 | JSON serialization custom replacement | SKIPPED - measured at 4.8% of total cost; risk of breaking fingerprint bytes |
| EXP5 | Memory/allocation micro-optimizations | SKIPPED - no measurably significant cost above what EXP3 already captures |
