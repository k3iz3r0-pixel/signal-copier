# Phase 1 — Step 9 Performance Baseline

## Environment

- Python: 3.13.15
- Python implementation: CPython
- Platform: Linux-7.0.0-30-generic-x86_64-with-glibc2.43
- Machine: x86_64
- Processor: unknown
- Logical CPU count: 12
- GC enabled: True
- Timestamp (UTC): 2026-08-31T00:34:30.740346+00:00
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
| canonical_validation | A_MINIMAL_SIGNAL | 5000 | 0.000005820 | 0.000004819 | 0.000006146 | 0.000007684 | 0.000002305 | 0.001016336 | 171820.4 | 7 | 7 |
| canonical_normalization | A_MINIMAL_SIGNAL | 5000 | 0.000006681 | 0.000006495 | 0.000007752 | 0.000013343 | 0.000003771 | 0.000431761 | 149670.5 | 7 | 7 |
| canonical_fingerprint | A_MINIMAL_SIGNAL | 5000 | 0.000014490 | 0.000014388 | 0.000018648 | 0.000029544 | 0.000010057 | 0.000052451 | 69014.6 | 7 | 7 |
| signal_construction | A_MINIMAL_SIGNAL | 5000 | 0.000010783 | 0.000010406 | 0.000012362 | 0.000025633 | 0.000006565 | 0.000474295 | 92740.5 | 7 | 7 |
| instruction_construction | A_MINIMAL_SIGNAL | 5000 | 0.000005720 | 0.000005657 | 0.000006775 | 0.000008738 | 0.000003771 | 0.000032406 | 174832.5 | 7 | 7 |
| revision_construction | A_MINIMAL_SIGNAL | 5000 | 0.000022506 | 0.000023397 | 0.000030520 | 0.000046096 | 0.000015156 | 0.000491546 | 44431.6 | 7 | 7 |
| event_construction | A_MINIMAL_SIGNAL | 5000 | 0.000006916 | 0.000006635 | 0.000008730 | 0.000009987 | 0.000004190 | 0.000127670 | 144582.5 | 7 | 7 |
| canonical_validation | B_NORMAL_SIGNAL | 5000 | 0.000010631 | 0.000010791 | 0.000012432 | 0.000026261 | 0.000006286 | 0.000389577 | 94065.7 | 10 | 12 |
| canonical_normalization | B_NORMAL_SIGNAL | 5000 | 0.000013470 | 0.000012991 | 0.000015296 | 0.000031013 | 0.000008172 | 0.001086527 | 74238.9 | 10 | 12 |
| canonical_fingerprint | B_NORMAL_SIGNAL | 5000 | 0.000028047 | 0.000029054 | 0.000035270 | 0.000050147 | 0.000019486 | 0.000755338 | 35654.0 | 10 | 12 |
| signal_construction | B_NORMAL_SIGNAL | 5000 | 0.000016197 | 0.000016622 | 0.000020044 | 0.000034085 | 0.000010546 | 0.000064324 | 61741.0 | 10 | 12 |
| instruction_construction | B_NORMAL_SIGNAL | 5000 | 0.000005320 | 0.000005238 | 0.000006565 | 0.000007054 | 0.000002793 | 0.000049448 | 187972.0 | 10 | 12 |
| revision_construction | B_NORMAL_SIGNAL | 5000 | 0.000046260 | 0.000045327 | 0.000056715 | 0.000070890 | 0.000031428 | 0.000202471 | 21616.9 | 10 | 12 |
| event_construction | B_NORMAL_SIGNAL | 5000 | 0.000007976 | 0.000007752 | 0.000009638 | 0.000010897 | 0.000004680 | 0.000043302 | 125377.2 | 10 | 12 |
| integrated_pipeline | B_NORMAL_SIGNAL | 5000 | 0.000083142 | 0.000082274 | 0.000101484 | 0.000113004 | 0.000050636 | 0.001715033 | 12027.6 | 10 | 12 |
| canonical_validation | C_LARGE_SIGNAL | 5000 | 0.000027506 | 0.000026260 | 0.000032686 | 0.000043373 | 0.000017181 | 0.000157353 | 36355.6 | 12 | 24 |
| canonical_normalization | C_LARGE_SIGNAL | 5000 | 0.000030898 | 0.000030521 | 0.000036461 | 0.000049589 | 0.000018928 | 0.000062997 | 32365.0 | 12 | 24 |
| canonical_fingerprint | C_LARGE_SIGNAL | 5000 | 0.000071075 | 0.000068165 | 0.000092889 | 0.000153514 | 0.000042394 | 0.004429079 | 14069.6 | 12 | 24 |
| signal_construction | C_LARGE_SIGNAL | 5000 | 0.000032445 | 0.000029054 | 0.000054553 | 0.000130752 | 0.000018927 | 0.000698835 | 30821.3 | 12 | 24 |
| instruction_construction | C_LARGE_SIGNAL | 5000 | 0.000005803 | 0.000005168 | 0.000006635 | 0.000017181 | 0.000002793 | 0.000510682 | 172311.5 | 12 | 24 |
| revision_construction | C_LARGE_SIGNAL | 5000 | 0.000112011 | 0.000109791 | 0.000134242 | 0.000230428 | 0.000068584 | 0.002696098 | 8927.7 | 12 | 24 |
| event_construction | C_LARGE_SIGNAL | 5000 | 0.000008745 | 0.000008521 | 0.000010127 | 0.000011874 | 0.000006146 | 0.000079410 | 114346.3 | 12 | 24 |
| canonical_validation | D_NESTED_SNAPSHOT | 5000 | 0.000006612 | 0.000006286 | 0.000007753 | 0.000008661 | 0.000004680 | 0.000099664 | 151248.9 | 6 | 20 |
| canonical_normalization | D_NESTED_SNAPSHOT | 5000 | 0.000008360 | 0.000008102 | 0.000009708 | 0.000012852 | 0.000004749 | 0.000119219 | 119618.7 | 6 | 20 |
| canonical_fingerprint | D_NESTED_SNAPSHOT | 5000 | 0.000022518 | 0.000022210 | 0.000024794 | 0.000041417 | 0.000013828 | 0.000216160 | 44408.6 | 6 | 20 |
| signal_construction | D_NESTED_SNAPSHOT | 5000 | 0.000012229 | 0.000012222 | 0.000014877 | 0.000027660 | 0.000006775 | 0.000383780 | 81775.0 | 6 | 20 |
| instruction_construction | D_NESTED_SNAPSHOT | 5000 | 0.000005289 | 0.000005238 | 0.000006285 | 0.000006775 | 0.000002793 | 0.000133886 | 189064.6 | 6 | 20 |
| revision_construction | D_NESTED_SNAPSHOT | 5000 | 0.000031079 | 0.000030521 | 0.000034851 | 0.000048749 | 0.000019555 | 0.000084857 | 32175.7 | 6 | 20 |
| event_construction | D_NESTED_SNAPSHOT | 5000 | 0.000008316 | 0.000008102 | 0.000009987 | 0.000011314 | 0.000004819 | 0.000039670 | 120245.8 | 6 | 20 |
| canonical_validation | E_MULTI_INSTRUCTION | 5000 | 0.000003074 | 0.000002933 | 0.000003841 | 0.000004260 | 0.000001396 | 0.000018578 | 325313.8 | 4 | 4 |
| canonical_normalization | E_MULTI_INSTRUCTION | 5000 | 0.000004160 | 0.000004260 | 0.000004820 | 0.000005308 | 0.000002305 | 0.000033873 | 240372.4 | 4 | 4 |
| canonical_fingerprint | E_MULTI_INSTRUCTION | 5000 | 0.000011560 | 0.000011384 | 0.000013410 | 0.000022566 | 0.000006705 | 0.000040369 | 86504.1 | 4 | 4 |
| signal_construction | E_MULTI_INSTRUCTION | 5000 | 0.000015472 | 0.000015156 | 0.000018159 | 0.000029125 | 0.000009498 | 0.000059924 | 64633.1 | 4 | 4 |
| instruction_construction | E_MULTI_INSTRUCTION | 5000 | 0.000005801 | 0.000005727 | 0.000006775 | 0.000007543 | 0.000002793 | 0.000027238 | 172390.5 | 4 | 4 |
| revision_construction | E_MULTI_INSTRUCTION | 5000 | 0.000019391 | 0.000016622 | 0.000019626 | 0.000037577 | 0.000010407 | 0.004969445 | 51571.4 | 4 | 4 |
| event_construction | E_MULTI_INSTRUCTION | 5000 | 0.000009233 | 0.000008521 | 0.000010057 | 0.000020395 | 0.000004889 | 0.000530797 | 108308.1 | 4 | 4 |
| canonical_validation | F_REVISION_CHAIN | 5000 | 0.000004542 | 0.000004261 | 0.000005308 | 0.000006076 | 0.000002305 | 0.000555800 | 220151.9 | 5 | 5 |
| canonical_normalization | F_REVISION_CHAIN | 5000 | 0.000006399 | 0.000005796 | 0.000007054 | 0.000007682 | 0.000003213 | 0.002299607 | 156269.1 | 5 | 5 |
| canonical_fingerprint | F_REVISION_CHAIN | 5000 | 0.000016986 | 0.000015854 | 0.000018368 | 0.000031430 | 0.000009917 | 0.001538053 | 58870.5 | 5 | 5 |
| signal_construction | F_REVISION_CHAIN | 5000 | 0.000010629 | 0.000010406 | 0.000012086 | 0.000022421 | 0.000006635 | 0.000038483 | 94086.3 | 5 | 5 |
| instruction_construction | F_REVISION_CHAIN | 5000 | 0.000006238 | 0.000006077 | 0.000007124 | 0.000007683 | 0.000003283 | 0.000403895 | 160314.8 | 5 | 5 |
| revision_construction | F_REVISION_CHAIN | 5000 | 0.000022591 | 0.000022629 | 0.000026331 | 0.000043721 | 0.000014248 | 0.000108813 | 44265.4 | 5 | 5 |
| event_construction | F_REVISION_CHAIN | 5000 | 0.000007733 | 0.000007683 | 0.000009918 | 0.000010966 | 0.000004190 | 0.000059017 | 129311.4 | 5 | 5 |

## Fingerprint scaling

| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 5000 | 0.000008036 | 0.000007961 | 0.000009428 | 0.000010406 | 0.000005168 | 0.000050705 | 124435.7 | 2 | 2 |
| medium | 5000 | 0.000018222 | 0.000017565 | 0.000021585 | 0.000036672 | 0.000010965 | 0.000178375 | 54878.8 | 8 | 9 |
| large | 5000 | 0.000200966 | 0.000203030 | 0.000233690 | 0.000252131 | 0.000131093 | 0.001844239 | 4976.0 | 12 | 133 |
| xlarge | 5000 | 0.000776223 | 0.000793681 | 0.000905919 | 0.001054129 | 0.000475761 | 0.006922217 | 1288.3 | 12 | 553 |

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
