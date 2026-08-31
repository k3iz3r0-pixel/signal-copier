# Phase 1 — Step 9 Performance Baseline

## Environment

- Python: 3.13.15
- Python implementation: CPython
- Platform: Linux-7.0.0-30-generic-x86_64-with-glibc2.43
- Machine: x86_64
- Processor: unknown
- Logical CPU count: 12
- GC enabled: True
- Timestamp (UTC): 2026-08-31T00:24:50.576697+00:00
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
| canonical_validation | A_MINIMAL_SIGNAL | 5000 | 0.000005368 | 0.000005168 | 0.000006216 | 0.000006706 | 0.000002794 | 0.000840754 | 186289.6 | 7 | 7 |
| canonical_normalization | A_MINIMAL_SIGNAL | 5000 | 0.000006888 | 0.000006705 | 0.000008032 | 0.000010477 | 0.000004260 | 0.000029543 | 145183.1 | 7 | 7 |
| canonical_fingerprint | A_MINIMAL_SIGNAL | 5000 | 0.000016622 | 0.000016343 | 0.000019486 | 0.000030871 | 0.000009848 | 0.000061112 | 60162.2 | 7 | 7 |
| signal_construction | A_MINIMAL_SIGNAL | 5000 | 0.000009710 | 0.000009568 | 0.000011454 | 0.000017183 | 0.000005797 | 0.000029124 | 102989.5 | 7 | 7 |
| instruction_construction | A_MINIMAL_SIGNAL | 5000 | 0.000005626 | 0.000005588 | 0.000006984 | 0.000008101 | 0.000003353 | 0.000023816 | 177738.9 | 7 | 7 |
| revision_construction | A_MINIMAL_SIGNAL | 5000 | 0.000027126 | 0.000027168 | 0.000030520 | 0.000044000 | 0.000016203 | 0.000201144 | 36865.3 | 7 | 7 |
| event_construction | A_MINIMAL_SIGNAL | 5000 | 0.000006835 | 0.000006146 | 0.000009498 | 0.000010337 | 0.000004190 | 0.000120197 | 146303.0 | 7 | 7 |
| canonical_validation | B_NORMAL_SIGNAL | 5000 | 0.000011056 | 0.000010616 | 0.000013130 | 0.000022279 | 0.000006216 | 0.000033315 | 90445.7 | 10 | 12 |
| canonical_normalization | B_NORMAL_SIGNAL | 5000 | 0.000013935 | 0.000013480 | 0.000015784 | 0.000027937 | 0.000008032 | 0.000058318 | 71760.9 | 10 | 12 |
| canonical_fingerprint | B_NORMAL_SIGNAL | 5000 | 0.000030868 | 0.000030940 | 0.000037086 | 0.000049449 | 0.000019066 | 0.000516549 | 32396.1 | 10 | 12 |
| signal_construction | B_NORMAL_SIGNAL | 5000 | 0.000016787 | 0.000016692 | 0.000020604 | 0.000031499 | 0.000010546 | 0.000427990 | 59568.2 | 10 | 12 |
| instruction_construction | B_NORMAL_SIGNAL | 5000 | 0.000005131 | 0.000005168 | 0.000006147 | 0.000006705 | 0.000002793 | 0.000046166 | 194883.3 | 10 | 12 |
| revision_construction | B_NORMAL_SIGNAL | 5000 | 0.000043264 | 0.000043581 | 0.000054616 | 0.000069703 | 0.000027867 | 0.003258882 | 23113.9 | 10 | 12 |
| event_construction | B_NORMAL_SIGNAL | 5000 | 0.000006375 | 0.000006076 | 0.000008451 | 0.000010481 | 0.000004260 | 0.000137588 | 156856.7 | 10 | 12 |
| integrated_pipeline | B_NORMAL_SIGNAL | 5000 | 0.000081004 | 0.000079968 | 0.000095896 | 0.000106789 | 0.000053429 | 0.000334751 | 12345.1 | 10 | 12 |
| canonical_validation | C_LARGE_SIGNAL | 5000 | 0.000027055 | 0.000027099 | 0.000032965 | 0.000044211 | 0.000015435 | 0.000237043 | 36961.6 | 12 | 24 |
| canonical_normalization | C_LARGE_SIGNAL | 5000 | 0.000031417 | 0.000031009 | 0.000035762 | 0.000047005 | 0.000020044 | 0.000127740 | 31829.9 | 12 | 24 |
| canonical_fingerprint | C_LARGE_SIGNAL | 5000 | 0.000072127 | 0.000070645 | 0.000085067 | 0.000099038 | 0.000043372 | 0.000505305 | 13864.5 | 12 | 24 |
| signal_construction | C_LARGE_SIGNAL | 5000 | 0.000032747 | 0.000032686 | 0.000038273 | 0.000053290 | 0.000018578 | 0.000277202 | 30536.8 | 12 | 24 |
| instruction_construction | C_LARGE_SIGNAL | 5000 | 0.000005505 | 0.000005308 | 0.000006565 | 0.000007124 | 0.000003352 | 0.000186616 | 181651.7 | 12 | 24 |
| revision_construction | C_LARGE_SIGNAL | 5000 | 0.000095102 | 0.000097778 | 0.000123340 | 0.000137939 | 0.000066349 | 0.000621032 | 10515.1 | 12 | 24 |
| event_construction | C_LARGE_SIGNAL | 5000 | 0.000007223 | 0.000007193 | 0.000009079 | 0.000009708 | 0.000004260 | 0.000033803 | 138437.9 | 12 | 24 |
| canonical_validation | D_NESTED_SNAPSHOT | 5000 | 0.000005900 | 0.000005867 | 0.000007683 | 0.000008173 | 0.000003282 | 0.000042394 | 169478.2 | 6 | 20 |
| canonical_normalization | D_NESTED_SNAPSHOT | 5000 | 0.000008601 | 0.000008450 | 0.000009638 | 0.000016835 | 0.000005168 | 0.000273012 | 116264.9 | 6 | 20 |
| canonical_fingerprint | D_NESTED_SNAPSHOT | 5000 | 0.000024415 | 0.000019696 | 0.000023746 | 0.000036109 | 0.000012851 | 0.010123202 | 40958.1 | 6 | 20 |
| signal_construction | D_NESTED_SNAPSHOT | 5000 | 0.000012803 | 0.000012152 | 0.000014181 | 0.000023890 | 0.000007612 | 0.002236959 | 78106.8 | 6 | 20 |
| instruction_construction | D_NESTED_SNAPSHOT | 5000 | 0.000005564 | 0.000005657 | 0.000006705 | 0.000007194 | 0.000003213 | 0.000044279 | 179732.9 | 6 | 20 |
| revision_construction | D_NESTED_SNAPSHOT | 5000 | 0.000028979 | 0.000029543 | 0.000034781 | 0.000049169 | 0.000019485 | 0.000106858 | 34507.7 | 6 | 20 |
| event_construction | D_NESTED_SNAPSHOT | 5000 | 0.000008331 | 0.000007263 | 0.000008731 | 0.000019486 | 0.000004190 | 0.001813579 | 120039.3 | 6 | 20 |
| canonical_validation | E_MULTI_INSTRUCTION | 5000 | 0.000002712 | 0.000002794 | 0.000003353 | 0.000003841 | 0.000000908 | 0.000091492 | 368780.8 | 4 | 4 |
| canonical_normalization | E_MULTI_INSTRUCTION | 5000 | 0.000003811 | 0.000003772 | 0.000004749 | 0.000005239 | 0.000001886 | 0.000046794 | 262401.1 | 4 | 4 |
| canonical_fingerprint | E_MULTI_INSTRUCTION | 5000 | 0.000010121 | 0.000010127 | 0.000012082 | 0.000021934 | 0.000006565 | 0.000106229 | 98801.5 | 4 | 4 |
| signal_construction | E_MULTI_INSTRUCTION | 5000 | 0.000015782 | 0.000015714 | 0.000018718 | 0.000031848 | 0.000009988 | 0.000328535 | 63363.6 | 4 | 4 |
| instruction_construction | E_MULTI_INSTRUCTION | 5000 | 0.000004898 | 0.000004749 | 0.000006285 | 0.000006775 | 0.000002793 | 0.000025352 | 204177.3 | 4 | 4 |
| revision_construction | E_MULTI_INSTRUCTION | 5000 | 0.000015889 | 0.000016273 | 0.000019835 | 0.000031012 | 0.000010476 | 0.000039461 | 62938.1 | 4 | 4 |
| event_construction | E_MULTI_INSTRUCTION | 5000 | 0.000008099 | 0.000008032 | 0.000009150 | 0.000010826 | 0.000004680 | 0.000178585 | 123468.6 | 4 | 4 |
| canonical_validation | F_REVISION_CHAIN | 5000 | 0.000004103 | 0.000004260 | 0.000005238 | 0.000005727 | 0.000002235 | 0.000021022 | 243715.5 | 5 | 5 |
| canonical_normalization | F_REVISION_CHAIN | 5000 | 0.000004997 | 0.000004749 | 0.000006704 | 0.000007194 | 0.000003282 | 0.000026679 | 200105.0 | 5 | 5 |
| canonical_fingerprint | F_REVISION_CHAIN | 5000 | 0.000014477 | 0.000014876 | 0.000017531 | 0.000028565 | 0.000009847 | 0.000531356 | 69073.4 | 5 | 5 |
| signal_construction | F_REVISION_CHAIN | 5000 | 0.000010940 | 0.000011035 | 0.000012851 | 0.000020399 | 0.000006286 | 0.000032825 | 91410.7 | 5 | 5 |
| instruction_construction | F_REVISION_CHAIN | 5000 | 0.000006806 | 0.000006705 | 0.000007683 | 0.000008243 | 0.000004679 | 0.000026260 | 146920.9 | 5 | 5 |
| revision_construction | F_REVISION_CHAIN | 5000 | 0.000021594 | 0.000022489 | 0.000027448 | 0.000039952 | 0.000014597 | 0.000049587 | 46309.2 | 5 | 5 |
| event_construction | F_REVISION_CHAIN | 5000 | 0.000008688 | 0.000008521 | 0.000009988 | 0.000011388 | 0.000005727 | 0.000031429 | 115104.1 | 5 | 5 |

## Fingerprint scaling

| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 5000 | 0.000008582 | 0.000008381 | 0.000009638 | 0.000010895 | 0.000005238 | 0.000157353 | 116520.5 | 2 | 2 |
| medium | 5000 | 0.000019452 | 0.000018927 | 0.000022000 | 0.000036667 | 0.000012153 | 0.000092470 | 51408.3 | 8 | 9 |
| large | 5000 | 0.000182358 | 0.000186547 | 0.000223214 | 0.000244454 | 0.000118731 | 0.002051739 | 5483.7 | 12 | 133 |
| xlarge | 5000 | 0.000753263 | 0.000759912 | 0.000881908 | 0.001038414 | 0.000472688 | 0.007163450 | 1327.6 | 12 | 553 |

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
