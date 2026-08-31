# Phase 1 — Step 9 Performance Baseline

## Environment

- Python: 3.13.15
- Python implementation: CPython
- Platform: Linux-7.0.0-30-generic-x86_64-with-glibc2.43
- Machine: x86_64
- Processor: unknown
- Logical CPU count: 12
- GC enabled: True
- Timestamp (UTC): 2026-08-31T00:47:19.995602+00:00
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
| canonical_validation | A_MINIMAL_SIGNAL | 5000 | 0.000004964 | 0.000004750 | 0.000006146 | 0.000006565 | 0.000003212 | 0.000081017 | 201451.0 | 7 | 7 |
| canonical_normalization | A_MINIMAL_SIGNAL | 5000 | 0.000006273 | 0.000006216 | 0.000007753 | 0.000009359 | 0.000003701 | 0.000039251 | 159419.4 | 7 | 7 |
| canonical_fingerprint | A_MINIMAL_SIGNAL | 5000 | 0.000012426 | 0.000012013 | 0.000014806 | 0.000023889 | 0.000007612 | 0.000047283 | 80475.7 | 7 | 7 |
| signal_construction | A_MINIMAL_SIGNAL | 5000 | 0.000009172 | 0.000009149 | 0.000011663 | 0.000013483 | 0.000005727 | 0.000042464 | 109028.7 | 7 | 7 |
| instruction_construction | A_MINIMAL_SIGNAL | 5000 | 0.000005096 | 0.000004750 | 0.000006705 | 0.000007194 | 0.000002794 | 0.000044349 | 196248.2 | 7 | 7 |
| revision_construction | A_MINIMAL_SIGNAL | 5000 | 0.000019685 | 0.000019696 | 0.000025073 | 0.000038135 | 0.000013758 | 0.000050286 | 50799.9 | 7 | 7 |
| event_construction | A_MINIMAL_SIGNAL | 5000 | 0.000008277 | 0.000008102 | 0.000009639 | 0.000010895 | 0.000005238 | 0.000046165 | 120809.6 | 7 | 7 |
| canonical_validation | B_NORMAL_SIGNAL | 5000 | 0.000011924 | 0.000011733 | 0.000013689 | 0.000022908 | 0.000007543 | 0.000044908 | 83866.3 | 10 | 12 |
| canonical_normalization | B_NORMAL_SIGNAL | 5000 | 0.000013566 | 0.000012990 | 0.000015225 | 0.000025286 | 0.000007962 | 0.000830626 | 73714.7 | 10 | 12 |
| canonical_fingerprint | B_NORMAL_SIGNAL | 5000 | 0.000023764 | 0.000022908 | 0.000027238 | 0.000040509 | 0.000015296 | 0.000789210 | 42080.1 | 10 | 12 |
| signal_construction | B_NORMAL_SIGNAL | 5000 | 0.000016224 | 0.000016623 | 0.000020533 | 0.000031988 | 0.000010336 | 0.000081715 | 61636.6 | 10 | 12 |
| instruction_construction | B_NORMAL_SIGNAL | 5000 | 0.000005192 | 0.000004889 | 0.000006077 | 0.000006565 | 0.000002794 | 0.000653089 | 192597.1 | 10 | 12 |
| revision_construction | B_NORMAL_SIGNAL | 5000 | 0.000033278 | 0.000028112 | 0.000045327 | 0.000059157 | 0.000023257 | 0.000103295 | 30049.6 | 10 | 12 |
| event_construction | B_NORMAL_SIGNAL | 5000 | 0.000008012 | 0.000007962 | 0.000009569 | 0.000010546 | 0.000004679 | 0.000038553 | 124805.8 | 10 | 12 |
| integrated_pipeline | B_NORMAL_SIGNAL | 5000 | 0.000075001 | 0.000073473 | 0.000090166 | 0.000102179 | 0.000047003 | 0.000894740 | 13333.1 | 10 | 12 |
| canonical_validation | C_LARGE_SIGNAL | 5000 | 0.000028313 | 0.000027587 | 0.000033803 | 0.000046096 | 0.000016762 | 0.000823223 | 35319.4 | 12 | 24 |
| canonical_normalization | C_LARGE_SIGNAL | 5000 | 0.000029283 | 0.000029403 | 0.000035270 | 0.000048052 | 0.000018089 | 0.000710638 | 34149.6 | 12 | 24 |
| canonical_fingerprint | C_LARGE_SIGNAL | 5000 | 0.000049797 | 0.000048540 | 0.000059575 | 0.000073824 | 0.000031429 | 0.000196325 | 20081.6 | 12 | 24 |
| signal_construction | C_LARGE_SIGNAL | 5000 | 0.000026764 | 0.000022838 | 0.000035689 | 0.000044072 | 0.000018857 | 0.002151540 | 37364.2 | 12 | 24 |
| instruction_construction | C_LARGE_SIGNAL | 5000 | 0.000005775 | 0.000005727 | 0.000006845 | 0.000007684 | 0.000002794 | 0.000254712 | 173147.5 | 12 | 24 |
| revision_construction | C_LARGE_SIGNAL | 5000 | 0.000085017 | 0.000085207 | 0.000102597 | 0.000114820 | 0.000052171 | 0.002294715 | 11762.4 | 12 | 24 |
| event_construction | C_LARGE_SIGNAL | 5000 | 0.000008177 | 0.000007962 | 0.000009638 | 0.000013414 | 0.000005168 | 0.000048330 | 122296.8 | 12 | 24 |
| canonical_validation | D_NESTED_SNAPSHOT | 5000 | 0.000006676 | 0.000006565 | 0.000008102 | 0.000008662 | 0.000003771 | 0.000067397 | 149779.3 | 6 | 20 |
| canonical_normalization | D_NESTED_SNAPSHOT | 5000 | 0.000007875 | 0.000007543 | 0.000009079 | 0.000014039 | 0.000005238 | 0.000697788 | 126981.4 | 6 | 20 |
| canonical_fingerprint | D_NESTED_SNAPSHOT | 5000 | 0.000014663 | 0.000014946 | 0.000016902 | 0.000030033 | 0.000009569 | 0.000086114 | 68200.4 | 6 | 20 |
| signal_construction | D_NESTED_SNAPSHOT | 5000 | 0.000012781 | 0.000012501 | 0.000014737 | 0.000024306 | 0.000007543 | 0.000051543 | 78243.6 | 6 | 20 |
| instruction_construction | D_NESTED_SNAPSHOT | 5000 | 0.000005184 | 0.000005168 | 0.000006216 | 0.000007124 | 0.000002793 | 0.000660143 | 192883.2 | 6 | 20 |
| revision_construction | D_NESTED_SNAPSHOT | 5000 | 0.000026424 | 0.000024864 | 0.000029054 | 0.000044630 | 0.000015715 | 0.001604610 | 37844.3 | 6 | 20 |
| event_construction | D_NESTED_SNAPSHOT | 5000 | 0.000008002 | 0.000007753 | 0.000009569 | 0.000010965 | 0.000004679 | 0.000509005 | 124973.4 | 6 | 20 |
| canonical_validation | E_MULTI_INSTRUCTION | 5000 | 0.000003254 | 0.000002933 | 0.000003841 | 0.000004330 | 0.000001396 | 0.000642193 | 307298.9 | 4 | 4 |
| canonical_normalization | E_MULTI_INSTRUCTION | 5000 | 0.000004408 | 0.000004330 | 0.000005238 | 0.000005657 | 0.000001956 | 0.000034153 | 226850.8 | 4 | 4 |
| canonical_fingerprint | E_MULTI_INSTRUCTION | 5000 | 0.000009258 | 0.000009010 | 0.000010616 | 0.000019066 | 0.000006705 | 0.000051683 | 108018.7 | 4 | 4 |
| signal_construction | E_MULTI_INSTRUCTION | 5000 | 0.000017485 | 0.000016832 | 0.000020045 | 0.000029543 | 0.000010895 | 0.000058388 | 57191.3 | 4 | 4 |
| instruction_construction | E_MULTI_INSTRUCTION | 5000 | 0.000005587 | 0.000005657 | 0.000006635 | 0.000007124 | 0.000003772 | 0.000054197 | 178972.1 | 4 | 4 |
| revision_construction | E_MULTI_INSTRUCTION | 5000 | 0.000016759 | 0.000016343 | 0.000018229 | 0.000031917 | 0.000009848 | 0.000839985 | 59668.9 | 4 | 4 |
| event_construction | E_MULTI_INSTRUCTION | 5000 | 0.000009532 | 0.000009009 | 0.000010476 | 0.000019910 | 0.000005169 | 0.001519893 | 104906.5 | 4 | 4 |
| canonical_validation | F_REVISION_CHAIN | 5000 | 0.000004753 | 0.000004749 | 0.000005797 | 0.000006216 | 0.000002374 | 0.000037715 | 210393.4 | 5 | 5 |
| canonical_normalization | F_REVISION_CHAIN | 5000 | 0.000005510 | 0.000005308 | 0.000007124 | 0.000007614 | 0.000003213 | 0.000052381 | 181492.0 | 5 | 5 |
| canonical_fingerprint | F_REVISION_CHAIN | 5000 | 0.000013048 | 0.000012781 | 0.000014667 | 0.000027238 | 0.000007962 | 0.000106438 | 76640.1 | 5 | 5 |
| signal_construction | F_REVISION_CHAIN | 5000 | 0.000011610 | 0.000010895 | 0.000012851 | 0.000024794 | 0.000006775 | 0.001462972 | 86131.2 | 5 | 5 |
| instruction_construction | F_REVISION_CHAIN | 5000 | 0.000006294 | 0.000006215 | 0.000007264 | 0.000008031 | 0.000003771 | 0.000043721 | 158872.6 | 5 | 5 |
| revision_construction | F_REVISION_CHAIN | 5000 | 0.000021366 | 0.000020604 | 0.000024026 | 0.000041416 | 0.000013759 | 0.000073054 | 46804.3 | 5 | 5 |
| event_construction | F_REVISION_CHAIN | 5000 | 0.000008588 | 0.000008172 | 0.000010057 | 0.000014624 | 0.000004749 | 0.000265398 | 116438.0 | 5 | 5 |

## Fingerprint scaling

| Label | Iter | Mean (s) | Median (s) | p95 (s) | p99 (s) | Min (s) | Max (s) | ops/s | Fields | Items |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 5000 | 0.000007204 | 0.000007123 | 0.000008242 | 0.000009575 | 0.000004819 | 0.000090514 | 138805.3 | 2 | 2 |
| medium | 5000 | 0.000013922 | 0.000013409 | 0.000015993 | 0.000027800 | 0.000009638 | 0.000125505 | 71828.8 | 8 | 9 |
| large | 5000 | 0.000145101 | 0.000136750 | 0.000167480 | 0.000298174 | 0.000085346 | 0.005290920 | 6891.7 | 12 | 133 |
| xlarge | 5000 | 0.000537574 | 0.000540399 | 0.000627817 | 0.000761163 | 0.000328674 | 0.003708100 | 1860.2 | 12 | 553 |

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
