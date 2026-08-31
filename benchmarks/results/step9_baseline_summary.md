# Phase 1 — Step 9 Performance Baseline

## Environment

- Python: 3.13.15
- Python implementation: CPython
- Platform: Linux-7.0.0-30-generic-x86_64-with-glibc2.43
- Machine: x86_64
- Processor: unknown
- Logical CPU count: 12
- GC enabled: True
- Timestamp (UTC): 2026-08-31T00:22:17.994577+00:00
- Benchmark tool: stdlib time.perf_counter_ns
- Timer: time.perf_counter_ns / time.perf_counter
- Iterations (default): 5000
- Warmups (default): 200

## Notes

- stdlib-only; no caches, no memoization, no multiprocessing.
- Setup time (fixture construction outside the timed loop) is explicitly excluded from the measured iteration.
- Throughput is operations per second derived from mean_seconds.
- Results are reproducible across runs with the same Python build and OS load; cross-hardware comparisons require qualification (see report).

## Operations

| Operation | Fixture | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| canonical_validation | A_MINIMAL_SIGNAL | 5000 | 0.000004715 | 0.000004261 | 0.000005311 | 0.000006216 | 0.000002304 | 0.000667966 | 212071.1 | 7 | 7 |
| canonical_normalization | A_MINIMAL_SIGNAL | 5000 | 0.000007034 | 0.000006495 | 0.000007752 | 0.000014743 | 0.000003771 | 0.001077518 | 142175.0 | 7 | 7 |
| canonical_fingerprint | A_MINIMAL_SIGNAL | 5000 | 0.000017451 | 0.000017181 | 0.000019486 | 0.000034924 | 0.000010616 | 0.000126902 | 57303.9 | 7 | 7 |
| signal_construction | A_MINIMAL_SIGNAL | 5000 | 0.000010003 | 0.000009987 | 0.000011943 | 0.000018509 | 0.000006076 | 0.000078152 | 99966.7 | 7 | 7 |
| instruction_construction | A_MINIMAL_SIGNAL | 5000 | 0.000005642 | 0.000005587 | 0.000006635 | 0.000007474 | 0.000002375 | 0.000213576 | 177226.5 | 7 | 7 |
| revision_construction | A_MINIMAL_SIGNAL | 5000 | 0.000027544 | 0.000025178 | 0.000029054 | 0.000045817 | 0.000016203 | 0.001524575 | 36305.9 | 7 | 7 |
| event_construction | A_MINIMAL_SIGNAL | 5000 | 0.000009685 | 0.000008102 | 0.000009708 | 0.000025771 | 0.000004749 | 0.001493564 | 103256.0 | 7 | 7 |
| canonical_validation | B_NORMAL_SIGNAL | 5000 | 0.000011231 | 0.000010337 | 0.000012571 | 0.000025632 | 0.000006495 | 0.002109149 | 89036.4 | 10 | 12 |
| canonical_normalization | B_NORMAL_SIGNAL | 5000 | 0.000014723 | 0.000013410 | 0.000015645 | 0.000031503 | 0.000008451 | 0.000895161 | 67921.4 | 10 | 12 |
| canonical_fingerprint | B_NORMAL_SIGNAL | 5000 | 0.000030374 | 0.000030731 | 0.000036178 | 0.000054268 | 0.000019626 | 0.001124312 | 32922.5 | 10 | 12 |
| signal_construction | B_NORMAL_SIGNAL | 5000 | 0.000017965 | 0.000018578 | 0.000021302 | 0.000035270 | 0.000010896 | 0.000085277 | 55662.7 | 10 | 12 |
| instruction_construction | B_NORMAL_SIGNAL | 5000 | 0.000005825 | 0.000005238 | 0.000006216 | 0.000013412 | 0.000002794 | 0.001656365 | 171680.6 | 10 | 12 |
| revision_construction | B_NORMAL_SIGNAL | 5000 | 0.000048502 | 0.000046584 | 0.000056296 | 0.000073126 | 0.000027657 | 0.001698480 | 20617.8 | 10 | 12 |
| event_construction | B_NORMAL_SIGNAL | 5000 | 0.000007451 | 0.000007682 | 0.000008870 | 0.000009989 | 0.000004679 | 0.000181868 | 134210.0 | 10 | 12 |
| integrated_pipeline | B_NORMAL_SIGNAL | 5000 | 0.000075101 | 0.000079969 | 0.000096312 | 0.000106863 | 0.000053010 | 0.000217138 | 13315.4 | 10 | 12 |
| canonical_validation | C_LARGE_SIGNAL | 5000 | 0.000024853 | 0.000025213 | 0.000031010 | 0.000041347 | 0.000015784 | 0.002329849 | 40236.5 | 12 | 24 |
| canonical_normalization | C_LARGE_SIGNAL | 5000 | 0.000029397 | 0.000030521 | 0.000034781 | 0.000049169 | 0.000019416 | 0.001367570 | 34016.6 | 12 | 24 |
| canonical_fingerprint | C_LARGE_SIGNAL | 5000 | 0.000068351 | 0.000070959 | 0.000085077 | 0.000092961 | 0.000045676 | 0.001436992 | 14630.3 | 12 | 24 |
| signal_construction | C_LARGE_SIGNAL | 5000 | 0.000030478 | 0.000031428 | 0.000036531 | 0.000049030 | 0.000018927 | 0.000232992 | 32810.1 | 12 | 24 |
| instruction_construction | C_LARGE_SIGNAL | 5000 | 0.000005663 | 0.000005657 | 0.000006635 | 0.000007124 | 0.000003352 | 0.000026261 | 176596.7 | 12 | 24 |
| revision_construction | C_LARGE_SIGNAL | 5000 | 0.000101372 | 0.000103994 | 0.000123969 | 0.000135634 | 0.000066210 | 0.000176909 | 9864.7 | 12 | 24 |
| event_construction | C_LARGE_SIGNAL | 5000 | 0.000008543 | 0.000008102 | 0.000009638 | 0.000010965 | 0.000004749 | 0.001451520 | 117057.9 | 12 | 24 |
| canonical_validation | D_NESTED_SNAPSHOT | 5000 | 0.000006116 | 0.000005238 | 0.000007543 | 0.000008032 | 0.000003352 | 0.001369177 | 163502.6 | 6 | 20 |
| canonical_normalization | D_NESTED_SNAPSHOT | 5000 | 0.000007779 | 0.000007752 | 0.000009429 | 0.000013899 | 0.000004679 | 0.000051264 | 128556.5 | 6 | 20 |
| canonical_fingerprint | D_NESTED_SNAPSHOT | 5000 | 0.000020192 | 0.000019311 | 0.000022632 | 0.000038692 | 0.000012292 | 0.003102717 | 49525.8 | 6 | 20 |
| signal_construction | D_NESTED_SNAPSHOT | 5000 | 0.000014188 | 0.000012083 | 0.000014387 | 0.000029544 | 0.000007613 | 0.003256998 | 70483.4 | 6 | 20 |
| instruction_construction | D_NESTED_SNAPSHOT | 5000 | 0.000006038 | 0.000005657 | 0.000006635 | 0.000007264 | 0.000003213 | 0.000850951 | 165606.7 | 6 | 20 |
| revision_construction | D_NESTED_SNAPSHOT | 5000 | 0.000032608 | 0.000030521 | 0.000038207 | 0.000055248 | 0.000012921 | 0.001327970 | 30667.3 | 6 | 20 |
| event_construction | D_NESTED_SNAPSHOT | 5000 | 0.000009035 | 0.000009009 | 0.000010196 | 0.000014666 | 0.000005238 | 0.000035270 | 110676.2 | 6 | 20 |
| canonical_validation | E_MULTI_INSTRUCTION | 5000 | 0.000002899 | 0.000002864 | 0.000003772 | 0.000003911 | 0.000000977 | 0.000028146 | 344982.2 | 4 | 4 |
| canonical_normalization | E_MULTI_INSTRUCTION | 5000 | 0.000004214 | 0.000004261 | 0.000005238 | 0.000005657 | 0.000001886 | 0.000026121 | 237308.9 | 4 | 4 |
| canonical_fingerprint | E_MULTI_INSTRUCTION | 5000 | 0.000010666 | 0.000010965 | 0.000013270 | 0.000020327 | 0.000004679 | 0.000041975 | 93753.6 | 4 | 4 |
| signal_construction | E_MULTI_INSTRUCTION | 5000 | 0.000014532 | 0.000014946 | 0.000018159 | 0.000031011 | 0.000009848 | 0.000261977 | 68815.7 | 4 | 4 |
| instruction_construction | E_MULTI_INSTRUCTION | 5000 | 0.000005882 | 0.000005308 | 0.000006635 | 0.000007755 | 0.000002794 | 0.001966742 | 170016.5 | 4 | 4 |
| revision_construction | E_MULTI_INSTRUCTION | 5000 | 0.000016940 | 0.000016692 | 0.000019838 | 0.000036459 | 0.000010336 | 0.000666569 | 59031.1 | 4 | 4 |
| event_construction | E_MULTI_INSTRUCTION | 5000 | 0.000007884 | 0.000007613 | 0.000009429 | 0.000013411 | 0.000004610 | 0.000721814 | 126834.9 | 4 | 4 |
| canonical_validation | F_REVISION_CHAIN | 5000 | 0.000004226 | 0.000003772 | 0.000004889 | 0.000005727 | 0.000001886 | 0.001742410 | 236619.0 | 5 | 5 |
| canonical_normalization | F_REVISION_CHAIN | 5000 | 0.000006182 | 0.000006147 | 0.000007473 | 0.000008241 | 0.000003282 | 0.000027378 | 161750.1 | 5 | 5 |
| canonical_fingerprint | F_REVISION_CHAIN | 5000 | 0.000018518 | 0.000016204 | 0.000018648 | 0.000031917 | 0.000009918 | 0.003118502 | 54000.4 | 5 | 5 |
| signal_construction | F_REVISION_CHAIN | 5000 | 0.000010564 | 0.000010406 | 0.000012293 | 0.000021945 | 0.000006565 | 0.000036317 | 94663.4 | 5 | 5 |
| instruction_construction | F_REVISION_CHAIN | 5000 | 0.000006371 | 0.000006216 | 0.000007542 | 0.000010689 | 0.000003283 | 0.000328465 | 156961.7 | 5 | 5 |
| revision_construction | F_REVISION_CHAIN | 5000 | 0.000025841 | 0.000025842 | 0.000029124 | 0.000043372 | 0.000015365 | 0.000070470 | 38698.6 | 5 | 5 |
| event_construction | F_REVISION_CHAIN | 5000 | 0.000007772 | 0.000007753 | 0.000009918 | 0.000013760 | 0.000004190 | 0.000050565 | 128670.7 | 5 | 5 |

## Fingerprint scaling

| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 5000 | 0.000008705 | 0.000008521 | 0.000009918 | 0.000017601 | 0.000005168 | 0.000034083 | 114870.1 | 2 | 2 |
| medium | 5000 | 0.000019528 | 0.000018788 | 0.000021581 | 0.000040020 | 0.000011873 | 0.000288866 | 51208.7 | 8 | 9 |
| large | 5000 | 0.000198108 | 0.000198560 | 0.000227415 | 0.000246124 | 0.000118242 | 0.002210769 | 5047.8 | 12 | 133 |
| xlarge | 5000 | 0.000765176 | 0.000791272 | 0.000914367 | 0.001075245 | 0.000466054 | 0.003043421 | 1306.9 | 12 | 553 |

## Memory

| Object | Shallow (bytes) | Deep current (bytes) | Deep peak (bytes) | Methodology |
|---|---:|---:|---:|---|
| Signal[B_NORMAL_SIGNAL] | 144 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| SignalRevision[B_NORMAL_SIGNAL] | 104 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| SignalInstruction[E_MULTI_INSTRUCTION] | 64 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| SignalEvent[B_NORMAL_SIGNAL] | 96 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| Signal[B_NORMAL_SIGNAL] | 144 | 1818 | 2746 | tracemalloc around single construction call |
| SignalRevision[B_NORMAL_SIGNAL] | 104 | 2867 | 4420 | tracemalloc around single construction call |
| SignalInstruction[E_MULTI_INSTRUCTION] | 64 | 806 | 902 | tracemalloc around single construction call |
| SignalEvent[B_NORMAL_SIGNAL] | 96 | 922 | 1327 | tracemalloc around single construction call |
| RevisionChain[F_REVISION_CHAIN] | 80 | n/a | n/a | list of 3 SignalRevision; shallow list size only |
