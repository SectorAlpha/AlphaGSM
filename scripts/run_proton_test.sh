#!/usr/bin/env bash
# Run a single proton integration test.
# Usage: bash scripts/run_proton_test.sh <module_name>
# Example: bash scripts/run_proton_test.sh theforestserver
set -euo pipefail

MODULE="${1:-theforestserver}"
WORK_DIR="${ALPHAGSM_WORK_DIR:-/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme}"

cd "$(git rev-parse --show-toplevel)"

ALPHAGSM_RUN_INTEGRATION=1 \
ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_WORK_DIR="$WORK_DIR" \
TMPDIR="$WORK_DIR" \
PYTHONPATH=.:src \
pytest "tests/integration_tests/test_${MODULE}.py" -v -s 2>&1
