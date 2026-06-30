#!/usr/bin/env bash
# Run the full CI pipeline locally — same steps as GitHub Actions.
# Usage: bash scripts/run_ci.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Ruff ==="
ruff check src/ tests/

echo "=== Black (check) ==="
black --check src/ tests/

echo "=== Mypy ==="
mypy src/ddo/backend/ src/ddo/models/ src/ddo/utils/

echo "=== Pytest ==="
pytest --cov=ddo --cov-report=term-missing -m "not gui" -x

echo ""
echo "All checks passed."
