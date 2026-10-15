#!/usr/bin/env bash
# Offline binding, hostname preflight, consent, protocol and no-replay gates.
set -euo pipefail
cd "$(dirname "$0")/../.."
PYTHONPATH=.:src "${PYTHON_BIN:-python3}" -m pytest \
  tests/unit_tests/agent tests/unit_tests/server/test_public_query.py \
  tests/unit_tests/utils/test_query.py -q
