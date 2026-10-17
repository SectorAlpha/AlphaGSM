#!/usr/bin/env bash
# First-run TTY/skip/replay and real CLI creation; no game downloads or launches.
set -euo pipefail
cd "$(dirname "$0")/../.."
PYTHONPATH=.:src "${PYTHON_BIN:-python3}" -m pytest \
  tests/unit_tests/core/test_welcome.py tests/integration_tests/test_first_run_tour.py -q
