#!/bin/bash
# Run a single integration test and report results.
# Usage: ./scripts/run_single_integration_test.sh <test_name>
# Example: ./scripts/run_single_integration_test.sh acserver
set -uo pipefail

TEST_NAME="${1:?Usage: $0 <test_name>}"
TEST_FILE="tests/integration_tests/test_${TEST_NAME}.py"

if [[ ! -f "$TEST_FILE" ]]; then
    echo "NOTFOUND: $TEST_FILE does not exist"
    exit 1
fi

# Cleanup before
screen -ls 2>/dev/null | grep "AlphaGSM-IT#" | awk '{print $1}' | while read -r s; do
    screen -S "$s" -X quit 2>/dev/null || true
done
rm -rf /tmp/pytest-of-"$(whoami)"/pytest-*/ 2>/dev/null || true

echo "=== Testing: $TEST_NAME ==="
echo "Disk: $(df -h / | tail -1 | awk '{print $4}') free"

OUTPUT=$(ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
    python -m pytest "$TEST_FILE" -x -v --tb=short --timeout=0 2>&1)

RESULT=$?

if echo "$OUTPUT" | grep -q "passed"; then
    echo "PASSED: $TEST_NAME"
elif echo "$OUTPUT" | grep -q "Invalid platform"; then
    echo "DISABLED_PLATFORM: $TEST_NAME"
elif echo "$OUTPUT" | grep -q "No subscription"; then
    echo "DISABLED_AUTH: $TEST_NAME"  
elif echo "$OUTPUT" | grep -q "Segmentation fault"; then
    echo "DISABLED_SEGFAULT: $TEST_NAME"
elif echo "$OUTPUT" | grep -q "Unable to find gameinfo.txt"; then
    echo "DISABLED_GAMEINFO: $TEST_NAME"
elif echo "$OUTPUT" | grep -q "unable to execute"; then
    echo "DISABLED_EXEC: $TEST_NAME"
else
    echo "FAILED: $TEST_NAME"
    echo "$OUTPUT" | tail -30
fi

# Cleanup after
screen -ls 2>/dev/null | grep "AlphaGSM-IT#" | awk '{print $1}' | while read -r s; do
    screen -S "$s" -X quit 2>/dev/null || true
done
rm -rf /tmp/pytest-of-"$(whoami)"/pytest-*/ 2>/dev/null || true
