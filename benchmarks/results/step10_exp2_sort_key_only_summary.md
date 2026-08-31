# Phase 1 — Step 9 Performance Baseline

## Environment

- Python: 3.13.15
- Python implementation: CPython
- Platform: Linux-7.0.0-30-generic-x86_64-with-glibc2.43
- Machine: x86_64
- Processor: unknown
- Logical CPU count: 12
- GC enabled: True
- Timestamp (UTC): 2026-08-31T00:26:36.398245+00:00
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
| canonical_validation | A_MINIMAL_SIGNAL | 5000 | 0.000005010 | 0.000004819 | 0.000006146 | 0.000006565 | 0.000001885 | 0.000060623 | 199612.8 | 7 | 7 |
| canonical_normalization | A_MINIMAL_SIGNAL | 5000 | 0.000006720 | 0.000006635 | 0.000007753 | 0.000012363 | 0.000003771 | 0.000042184 | 148806.8 | 7 | 7 |
| canonical_fingerprint | A_MINIMAL_SIGNAL | 5000 | 0.000017903 | 0.000017390 | 0.000020114 | 0.000034854 | 0.000011035 | 0.000097290 | 55857.0 | 7 | 7 |
| signal_construction | A_MINIMAL_SIGNAL | 5000 | 0.000009471 | 0.000009569 | 0.000011524 | 0.000013270 | 0.000005867 | 0.000048330 | 105583.3 | 7 | 7 |
| instruction_construction | A_MINIMAL_SIGNAL | 5000 | 0.000004904 | 0.000004819 | 0.000006077 | 0.000006635 | 0.000002793 | 0.000026750 | 203916.9 | 7 | 7 |
| revision_construction | A_MINIMAL_SIGNAL | 5000 | 0.000024989 | 0.000024864 | 0.000029966 | 0.000042882 | 0.000015714 | 0.000074311 | 40017.0 | 7 | 7 |
| event_construction | A_MINIMAL_SIGNAL | 5000 | 0.000008923 | 0.000008661 | 0.000010407 | 0.000011734 | 0.000005098 | 0.000030521 | 112070.1 | 7 | 7 |
| canonical_validation | B_NORMAL_SIGNAL | 5000 | 0.000009416 | 0.000008242 | 0.000012851 | 0.000014550 | 0.000006495 | 0.000043302 | 106202.0 | 10 | 12 |
| canonical_normalization | B_NORMAL_SIGNAL | 5000 | 0.000012511 | 0.000012921 | 0.000015715 | 0.000022280 | 0.000007473 | 0.000485260 | 79928.8 | 10 | 12 |
| canonical_fingerprint | B_NORMAL_SIGNAL | 5000 | 0.000033834 | 0.000033315 | 0.000037788 | 0.000050566 | 0.000021442 | 0.000269659 | 29556.3 | 10 | 12 |
| signal_construction | B_NORMAL_SIGNAL | 5000 | 0.000018545 | 0.000018020 | 0.000021305 | 0.000031498 | 0.000011384 | 0.000065372 | 53921.8 | 10 | 12 |
| instruction_construction | B_NORMAL_SIGNAL | 5000 | 0.000006074 | 0.000006076 | 0.000007054 | 0.000007612 | 0.000003912 | 0.000050844 | 164642.5 | 10 | 12 |
| revision_construction | B_NORMAL_SIGNAL | 5000 | 0.000049587 | 0.000049238 | 0.000058178 | 0.000070541 | 0.000029473 | 0.000083950 | 20166.5 | 10 | 12 |
| event_construction | B_NORMAL_SIGNAL | 5000 | 0.000007054 | 0.000007054 | 0.000009150 | 0.000009987 | 0.000004260 | 0.000035270 | 141758.5 | 10 | 12 |
| integrated_pipeline | B_NORMAL_SIGNAL | 5000 | 0.000076015 | 0.000077804 | 0.000093937 | 0.000107208 | 0.000052451 | 0.003216559 | 13155.3 | 10 | 12 |
| canonical_validation | C_LARGE_SIGNAL | 5000 | 0.000028926 | 0.000029089 | 0.000033384 | 0.000042884 | 0.000017321 | 0.000157354 | 34570.5 | 12 | 24 |
| canonical_normalization | C_LARGE_SIGNAL | 5000 | 0.000029508 | 0.000029543 | 0.000035270 | 0.000046794 | 0.000017740 | 0.000163778 | 33889.4 | 12 | 24 |
| canonical_fingerprint | C_LARGE_SIGNAL | 5000 | 0.000071453 | 0.000070609 | 0.000084927 | 0.000096243 | 0.000045886 | 0.000360522 | 13995.1 | 12 | 24 |
| signal_construction | C_LARGE_SIGNAL | 5000 | 0.000032255 | 0.000032896 | 0.000038553 | 0.000051265 | 0.000018508 | 0.000237741 | 31002.7 | 12 | 24 |
| instruction_construction | C_LARGE_SIGNAL | 5000 | 0.000005765 | 0.000005727 | 0.000006705 | 0.000007194 | 0.000003911 | 0.000028566 | 173459.2 | 12 | 24 |
| revision_construction | C_LARGE_SIGNAL | 5000 | 0.000109729 | 0.000108604 | 0.000128020 | 0.000142897 | 0.000064813 | 0.004338844 | 9113.4 | 12 | 24 |
| event_construction | C_LARGE_SIGNAL | 5000 | 0.000008630 | 0.000008242 | 0.000009918 | 0.000011384 | 0.000004749 | 0.000227125 | 115869.8 | 12 | 24 |
| canonical_validation | D_NESTED_SNAPSHOT | 5000 | 0.000006206 | 0.000006146 | 0.000007682 | 0.000008172 | 0.000003282 | 0.000116914 | 161144.9 | 6 | 20 |
| canonical_normalization | D_NESTED_SNAPSHOT | 5000 | 0.000008426 | 0.000008171 | 0.000009638 | 0.000013829 | 0.000004749 | 0.000221817 | 118684.6 | 6 | 20 |
| canonical_fingerprint | D_NESTED_SNAPSHOT | 5000 | 0.000020563 | 0.000020045 | 0.000023048 | 0.000035341 | 0.000012082 | 0.000198979 | 48630.2 | 6 | 20 |
| signal_construction | D_NESTED_SNAPSHOT | 5000 | 0.000012881 | 0.000012781 | 0.000014876 | 0.000025773 | 0.000007054 | 0.000037156 | 77631.4 | 6 | 20 |
| instruction_construction | D_NESTED_SNAPSHOT | 5000 | 0.000005253 | 0.000005238 | 0.000006216 | 0.000006775 | 0.000002864 | 0.000024305 | 190368.9 | 6 | 20 |
| revision_construction | D_NESTED_SNAPSHOT | 5000 | 0.000032233 | 0.000031988 | 0.000036247 | 0.000051334 | 0.000019555 | 0.000077384 | 31024.2 | 6 | 20 |
| event_construction | D_NESTED_SNAPSHOT | 5000 | 0.000007478 | 0.000007543 | 0.000009428 | 0.000010966 | 0.000003911 | 0.000106229 | 133722.8 | 6 | 20 |
| canonical_validation | E_MULTI_INSTRUCTION | 5000 | 0.000003129 | 0.000002933 | 0.000003841 | 0.000004260 | 0.000001816 | 0.000023955 | 319593.3 | 4 | 4 |
| canonical_normalization | E_MULTI_INSTRUCTION | 5000 | 0.000004372 | 0.000004261 | 0.000005169 | 0.000005309 | 0.000002305 | 0.000350046 | 228713.8 | 4 | 4 |
| canonical_fingerprint | E_MULTI_INSTRUCTION | 5000 | 0.000011152 | 0.000010896 | 0.000012920 | 0.000022982 | 0.000006635 | 0.000042324 | 89671.9 | 4 | 4 |
| signal_construction | E_MULTI_INSTRUCTION | 5000 | 0.000016330 | 0.000015714 | 0.000018577 | 0.000031498 | 0.000009918 | 0.000408085 | 61235.5 | 4 | 4 |
| instruction_construction | E_MULTI_INSTRUCTION | 5000 | 0.000005596 | 0.000005657 | 0.000006635 | 0.000007123 | 0.000003282 | 0.000025352 | 178690.0 | 4 | 4 |
| revision_construction | E_MULTI_INSTRUCTION | 5000 | 0.000017869 | 0.000017531 | 0.000020045 | 0.000034781 | 0.000011314 | 0.000186547 | 55963.8 | 4 | 4 |
| event_construction | E_MULTI_INSTRUCTION | 5000 | 0.000007705 | 0.000007612 | 0.000009080 | 0.000010057 | 0.000004749 | 0.000044908 | 129790.9 | 4 | 4 |
| canonical_validation | F_REVISION_CHAIN | 5000 | 0.000004459 | 0.000004330 | 0.000005308 | 0.000005797 | 0.000002374 | 0.000031009 | 224248.7 | 5 | 5 |
| canonical_normalization | F_REVISION_CHAIN | 5000 | 0.000006804 | 0.000006565 | 0.000007543 | 0.000008521 | 0.000003352 | 0.000612861 | 146981.7 | 5 | 5 |
| canonical_fingerprint | F_REVISION_CHAIN | 5000 | 0.000017028 | 0.000017111 | 0.000018997 | 0.000031430 | 0.000009987 | 0.000044978 | 58725.8 | 5 | 5 |
| signal_construction | F_REVISION_CHAIN | 5000 | 0.000009432 | 0.000009568 | 0.000011942 | 0.000013704 | 0.000005657 | 0.000156096 | 106020.0 | 5 | 5 |
| instruction_construction | F_REVISION_CHAIN | 5000 | 0.000006103 | 0.000006146 | 0.000007194 | 0.000007752 | 0.000003282 | 0.000040928 | 163847.9 | 5 | 5 |
| revision_construction | F_REVISION_CHAIN | 5000 | 0.000024385 | 0.000024025 | 0.000027658 | 0.000040858 | 0.000014736 | 0.000196534 | 41009.2 | 5 | 5 |
| event_construction | F_REVISION_CHAIN | 5000 | 0.000008161 | 0.000008031 | 0.000009568 | 0.000010616 | 0.000005308 | 0.000026191 | 122535.4 | 5 | 5 |

## Fingerprint scaling

| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 5000 | 0.000009205 | 0.000009009 | 0.000010407 | 0.000012438 | 0.000005238 | 0.000489939 | 108637.4 | 2 | 2 |
| medium | 5000 | 0.000018990 | 0.000018508 | 0.000022000 | 0.000032895 | 0.000011803 | 0.000108255 | 52657.9 | 8 | 9 |
| large | 5000 | 0.000186645 | 0.000192763 | 0.000225449 | 0.000239420 | 0.000116565 | 0.003376146 | 5357.8 | 12 | 133 |
| xlarge | 5000 | 0.000759239 | 0.000785859 | 0.000910197 | 0.000962356 | 0.000464866 | 0.004697132 | 1317.1 | 12 | 553 |

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
