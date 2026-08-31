# Phase 1 — Step 9 Performance Baseline

## Environment

- Python: 3.13.15
- Python implementation: CPython
- Platform: Linux-7.0.0-30-generic-x86_64-with-glibc2.43
- Machine: x86_64
- Processor: unknown
- Logical CPU count: 12
- GC enabled: True
- Timestamp (UTC): 2026-08-31T00:45:16.344857+00:00
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
| canonical_validation | A_MINIMAL_SIGNAL | 5000 | 0.000007695 | 0.000004749 | 0.000005727 | 0.000006286 | 0.000002305 | 0.009790185 | 129950.4 | 7 | 7 |
| canonical_normalization | A_MINIMAL_SIGNAL | 5000 | 0.000006241 | 0.000006146 | 0.000007264 | 0.000015300 | 0.000003283 | 0.000432180 | 160235.3 | 7 | 7 |
| canonical_fingerprint | A_MINIMAL_SIGNAL | 5000 | 0.000011264 | 0.000011105 | 0.000013759 | 0.000021308 | 0.000007054 | 0.000861636 | 88780.3 | 7 | 7 |
| signal_construction | A_MINIMAL_SIGNAL | 5000 | 0.000010470 | 0.000010127 | 0.000011943 | 0.000021025 | 0.000006216 | 0.000163150 | 95507.2 | 7 | 7 |
| instruction_construction | A_MINIMAL_SIGNAL | 5000 | 0.000006209 | 0.000005238 | 0.000006286 | 0.000007124 | 0.000003282 | 0.003781853 | 161048.2 | 7 | 7 |
| revision_construction | A_MINIMAL_SIGNAL | 5000 | 0.000019946 | 0.000020499 | 0.000024235 | 0.000036740 | 0.000013759 | 0.000267284 | 50134.2 | 7 | 7 |
| event_construction | A_MINIMAL_SIGNAL | 5000 | 0.000007611 | 0.000007613 | 0.000009429 | 0.000010406 | 0.000004679 | 0.000035689 | 131389.2 | 7 | 7 |
| canonical_validation | B_NORMAL_SIGNAL | 5000 | 0.000010321 | 0.000009848 | 0.000011873 | 0.000018929 | 0.000006146 | 0.001036868 | 96885.3 | 10 | 12 |
| canonical_normalization | B_NORMAL_SIGNAL | 5000 | 0.000011576 | 0.000011524 | 0.000014527 | 0.000023958 | 0.000007962 | 0.000323856 | 86387.8 | 10 | 12 |
| canonical_fingerprint | B_NORMAL_SIGNAL | 5000 | 0.000021733 | 0.000021022 | 0.000026680 | 0.000040162 | 0.000013200 | 0.003630855 | 46012.0 | 10 | 12 |
| signal_construction | B_NORMAL_SIGNAL | 5000 | 0.000016394 | 0.000016622 | 0.000020533 | 0.000032480 | 0.000010546 | 0.000049937 | 60997.4 | 10 | 12 |
| instruction_construction | B_NORMAL_SIGNAL | 5000 | 0.000004737 | 0.000004679 | 0.000006146 | 0.000006635 | 0.000002793 | 0.000031498 | 211101.2 | 10 | 12 |
| revision_construction | B_NORMAL_SIGNAL | 5000 | 0.000037796 | 0.000037156 | 0.000043721 | 0.000058319 | 0.000023257 | 0.000102039 | 26457.9 | 10 | 12 |
| event_construction | B_NORMAL_SIGNAL | 5000 | 0.000007990 | 0.000007752 | 0.000009568 | 0.000010897 | 0.000004330 | 0.000070959 | 125153.5 | 10 | 12 |
| integrated_pipeline | B_NORMAL_SIGNAL | 5000 | 0.000070682 | 0.000071029 | 0.000090096 | 0.000104203 | 0.000044699 | 0.000259043 | 14147.9 | 10 | 12 |
| canonical_validation | C_LARGE_SIGNAL | 5000 | 0.000026908 | 0.000026260 | 0.000031917 | 0.000048262 | 0.000017460 | 0.000163848 | 37163.4 | 12 | 24 |
| canonical_normalization | C_LARGE_SIGNAL | 5000 | 0.000027551 | 0.000027587 | 0.000032896 | 0.000050496 | 0.000018997 | 0.000243678 | 36296.5 | 12 | 24 |
| canonical_fingerprint | C_LARGE_SIGNAL | 5000 | 0.000050489 | 0.000048889 | 0.000062442 | 0.000091578 | 0.000031010 | 0.000364364 | 19806.4 | 12 | 24 |
| signal_construction | C_LARGE_SIGNAL | 5000 | 0.000029421 | 0.000029194 | 0.000036042 | 0.000053919 | 0.000018508 | 0.001425676 | 33989.1 | 12 | 24 |
| instruction_construction | C_LARGE_SIGNAL | 5000 | 0.000006022 | 0.000005727 | 0.000006705 | 0.000007613 | 0.000003282 | 0.000178096 | 166055.2 | 12 | 24 |
| revision_construction | C_LARGE_SIGNAL | 5000 | 0.000081837 | 0.000081436 | 0.000101619 | 0.000113074 | 0.000053359 | 0.000995871 | 12219.4 | 12 | 24 |
| event_construction | C_LARGE_SIGNAL | 5000 | 0.000008640 | 0.000008521 | 0.000009918 | 0.000011315 | 0.000004679 | 0.000415069 | 115741.7 | 12 | 24 |
| canonical_validation | D_NESTED_SNAPSHOT | 5000 | 0.000007213 | 0.000007124 | 0.000008172 | 0.000009149 | 0.000005098 | 0.000079131 | 138638.9 | 6 | 20 |
| canonical_normalization | D_NESTED_SNAPSHOT | 5000 | 0.000008322 | 0.000008171 | 0.000009572 | 0.000013620 | 0.000004679 | 0.000042882 | 120163.0 | 6 | 20 |
| canonical_fingerprint | D_NESTED_SNAPSHOT | 5000 | 0.000014426 | 0.000014597 | 0.000017740 | 0.000028916 | 0.000009219 | 0.000947611 | 69317.2 | 6 | 20 |
| signal_construction | D_NESTED_SNAPSHOT | 5000 | 0.000012898 | 0.000012432 | 0.000014737 | 0.000027170 | 0.000007752 | 0.000296687 | 77529.3 | 6 | 20 |
| instruction_construction | D_NESTED_SNAPSHOT | 5000 | 0.000005647 | 0.000005657 | 0.000006704 | 0.000007193 | 0.000003423 | 0.000028565 | 177073.3 | 6 | 20 |
| revision_construction | D_NESTED_SNAPSHOT | 5000 | 0.000026868 | 0.000026260 | 0.000030102 | 0.000043721 | 0.000017390 | 0.000859680 | 37218.6 | 6 | 20 |
| event_construction | D_NESTED_SNAPSHOT | 5000 | 0.000008440 | 0.000008171 | 0.000009987 | 0.000011107 | 0.000005308 | 0.000053778 | 118476.5 | 6 | 20 |
| canonical_validation | E_MULTI_INSTRUCTION | 5000 | 0.000003263 | 0.000003282 | 0.000003841 | 0.000004330 | 0.000001467 | 0.000178445 | 306465.3 | 4 | 4 |
| canonical_normalization | E_MULTI_INSTRUCTION | 5000 | 0.000004336 | 0.000004261 | 0.000005169 | 0.000005378 | 0.000002375 | 0.000021093 | 230617.0 | 4 | 4 |
| canonical_fingerprint | E_MULTI_INSTRUCTION | 5000 | 0.000008084 | 0.000008171 | 0.000010058 | 0.000011035 | 0.000005238 | 0.000028077 | 123702.1 | 4 | 4 |
| signal_construction | E_MULTI_INSTRUCTION | 5000 | 0.000016896 | 0.000017041 | 0.000019626 | 0.000031639 | 0.000010406 | 0.000062858 | 59186.8 | 4 | 4 |
| instruction_construction | E_MULTI_INSTRUCTION | 5000 | 0.000006251 | 0.000006215 | 0.000007124 | 0.000007613 | 0.000003283 | 0.000224401 | 159963.9 | 4 | 4 |
| revision_construction | E_MULTI_INSTRUCTION | 5000 | 0.000014743 | 0.000014946 | 0.000017879 | 0.000030037 | 0.000009009 | 0.000236763 | 67828.9 | 4 | 4 |
| event_construction | E_MULTI_INSTRUCTION | 5000 | 0.000011537 | 0.000008730 | 0.000010127 | 0.000011455 | 0.000006565 | 0.012826547 | 86679.7 | 4 | 4 |
| canonical_validation | F_REVISION_CHAIN | 5000 | 0.000004990 | 0.000004819 | 0.000005797 | 0.000006286 | 0.000002794 | 0.000019626 | 200402.2 | 5 | 5 |
| canonical_normalization | F_REVISION_CHAIN | 5000 | 0.000006354 | 0.000006216 | 0.000007264 | 0.000007754 | 0.000003353 | 0.000108953 | 157382.4 | 5 | 5 |
| canonical_fingerprint | F_REVISION_CHAIN | 5000 | 0.000013204 | 0.000012921 | 0.000014806 | 0.000027169 | 0.000008102 | 0.000082552 | 75733.1 | 5 | 5 |
| signal_construction | F_REVISION_CHAIN | 5000 | 0.000011104 | 0.000010616 | 0.000012781 | 0.000024520 | 0.000006565 | 0.000166433 | 90058.8 | 5 | 5 |
| instruction_construction | F_REVISION_CHAIN | 5000 | 0.000006206 | 0.000006146 | 0.000007194 | 0.000007753 | 0.000003282 | 0.000043302 | 161124.5 | 5 | 5 |
| revision_construction | F_REVISION_CHAIN | 5000 | 0.000022397 | 0.000019346 | 0.000023330 | 0.000044282 | 0.000012921 | 0.003144338 | 44649.7 | 5 | 5 |
| event_construction | F_REVISION_CHAIN | 5000 | 0.000009069 | 0.000008451 | 0.000009988 | 0.000020394 | 0.000004889 | 0.000810651 | 110261.5 | 5 | 5 |

## Fingerprint scaling

| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 5000 | 0.000007127 | 0.000006356 | 0.000008102 | 0.000015024 | 0.000003771 | 0.000725724 | 140314.3 | 2 | 2 |
| medium | 5000 | 0.000012836 | 0.000012501 | 0.000014876 | 0.000027239 | 0.000008381 | 0.000976804 | 77908.6 | 8 | 9 |
| large | 5000 | 0.000134803 | 0.000135563 | 0.000161198 | 0.000181591 | 0.000091074 | 0.003822081 | 7418.2 | 12 | 133 |
| xlarge | 5000 | 0.000532035 | 0.000541237 | 0.000618312 | 0.000649876 | 0.000334052 | 0.006658558 | 1879.6 | 12 | 553 |

## Memory

| Object | Shallow (bytes) | Deep current (bytes) | Deep peak (bytes) | Methodology |
|---|---:|---:|---:|---|
| Signal[B_NORMAL_SIGNAL] | 144 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| SignalRevision[B_NORMAL_SIGNAL] | 104 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| SignalInstruction[E_MULTI_INSTRUCTION] | 64 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| SignalEvent[B_NORMAL_SIGNAL] | 96 | n/a | n/a | sys.getsizeof (shallow only; excludes nested members) |
| Signal[B_NORMAL_SIGNAL] | 144 | 1818 | 2746 | tracemalloc around single construction call |
| SignalRevision[B_NORMAL_SIGNAL] | 104 | 2971 | 4700 | tracemalloc around single construction call |
| SignalInstruction[E_MULTI_INSTRUCTION] | 64 | 806 | 902 | tracemalloc around single construction call |
| SignalEvent[B_NORMAL_SIGNAL] | 96 | 922 | 1327 | tracemalloc around single construction call |
| RevisionChain[F_REVISION_CHAIN] | 80 | n/a | n/a | list of 3 SignalRevision; shallow list size only |
