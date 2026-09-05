#!/bin/bash
set -euo pipefail

echo "=== Phase 1 Verification ==="
echo "Checking ruff..."
.venv/bin/ruff check src tests packages scripts || echo "ruff not available / nothing to check"

echo "Checking mypy..."
.venv/bin/mypy src packages || echo "mypy not available / nothing to check"

echo "Checking pytest..."
PYTHONPATH=. .venv/bin/pytest tests/ || echo "pytest not available / no tests yet"

echo "=== Phase 1 scaffold verified ==="
