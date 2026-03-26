#!/bin/bash
# Run a single integration test and report result
# Usage: ./run_single_integration_test.sh <test_name>
# Example: ./run_single_integration_test.sh arma2coserver

set -u
TEST_NAME="$1"
TEST_FILE="tests/integration_tests/test_${TEST_NAME}.py"
BASEDIR="/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme/agsm-it-${TEST_NAME}"

if [[ ! -f "$TEST_FILE" ]]; then
    echo "RESULT:${TEST_NAME}:ERROR:Test file not found: ${TEST_FILE}"
    exit 1
fi

echo "=== Running: ${TEST_NAME} ==="
echo "Start: $(date '+%H:%M:%S')"

rm -rf "$BASEDIR" 2>/dev/null

ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 PYTHONPATH=src \
    python3 -m pytest "$TEST_FILE" -v --timeout=1200 -x -s --basetemp="$BASEDIR" 2>&1 | tail -50

RC=${PIPESTATUS[0]}
echo "End: $(date '+%H:%M:%S')"

# Cleanup
rm -rf "$BASEDIR" 2>/dev/null

if [[ $RC -eq 0 ]]; then
    echo "RESULT:${TEST_NAME}:PASSED"
else
    echo "RESULT:${TEST_NAME}:FAILED:rc=${RC}"
fi

echo "Disk: $(df -h / | tail -1 | awk '{print $4}') free"
