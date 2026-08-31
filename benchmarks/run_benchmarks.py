"""Phase 1 — Step 9: Performance baseline CLI entry point.

Run from repo root::

    PYTHONPATH=. python benchmarks/run_benchmarks.py

Writes:

- benchmarks/results/benchmark_report.json
- benchmarks/results/benchmark_summary.md

Does not modify any production code.
"""

from __future__ import annotations

import sys

from benchmarks.runner import (
    DEFAULT_ITERATIONS,
    DEFAULT_WARMUPS,
    RESULTS_DIR,
    run_all_benchmarks,
    write_markdown_summary,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    iterations = DEFAULT_ITERATIONS
    warmups = DEFAULT_WARMUPS
    for arg in argv:
        if arg.startswith("--iterations="):
            iterations = int(arg.split("=", 1)[1])
        elif arg.startswith("--warmups="):
            warmups = int(arg.split("=", 1)[1])
        elif arg == "--help" or arg == "-h":
            print(__doc__)
            return 0

    print(
        f"Phase 1 — Step 9: running benchmarks "
        f"(iterations={iterations}, warmups={warmups})"
    )

    report = run_all_benchmarks(iterations=iterations, warmups=warmups)

    json_path = RESULTS_DIR / "benchmark_report.json"
    md_path = RESULTS_DIR / "benchmark_summary.md"
    write_report(report, json_path)
    write_markdown_summary(report, md_path)
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote Markdown: {md_path}")
    print(
        f"Operations measured: {len(report.operations)}; "
        f"fingerprint-scaling points: {len(report.fingerprint_scaling)}; "
        f"memory rows: {len(report.memory)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
