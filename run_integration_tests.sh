#!/usr/bin/env bash
# Run integration tests one at a time and clean up downloads between each.
# Usage:
#   bash run_integration_tests.sh                # run all
#   bash run_integration_tests.sh test_foo.py    # run one specific file
#   bash run_integration_tests.sh --pytest-args "-v"  # extra pytest flags
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IT_DIR="${SCRIPT_DIR}/integration_tests"
export PYTHONPATH=".:src${PYTHONPATH:+:$PYTHONPATH}"

# Accept optional extra pytest args after --pytest-args
PYTEST_EXTRA=()
FILES=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pytest-args)
            shift
            while [[ $# -gt 0 ]]; do
                PYTEST_EXTRA+=("$1")
                shift
            done
            ;;
        *)
            FILES+=("$1")
            shift
            ;;
    esac
done

# If no files specified, discover all test files
if [[ ${#FILES[@]} -eq 0 ]]; then
    while IFS= read -r f; do
        FILES+=("$f")
    done < <(find "$IT_DIR" -maxdepth 1 -name 'test_*.py' -type f | sort)
fi

TOTAL=${#FILES[@]}
PASSED=0
FAILED=0
SKIPPED=0
FAIL_LIST=()

cleanup_tmp() {
    # Remove pytest tmp dirs to free disk space after each test
    rm -rf /tmp/pytest-of-"$(whoami)"/pytest-*/
    # Kill any leftover integration-test screen sessions
    screen -ls 2>/dev/null | grep -oP 'AlphaGSM-IT#\S+' | while read -r sess; do
        screen -S "$sess" -X quit 2>/dev/null || true
    done
}

echo "=== Running ${TOTAL} integration test file(s) one by one ==="
echo ""

for i in "${!FILES[@]}"; do
    FILE="${FILES[$i]}"
    BASENAME="$(basename "$FILE")"
    IDX=$((i + 1))
    echo "--- [${IDX}/${TOTAL}] ${BASENAME} ---"

    if pytest "$FILE" "${PYTEST_EXTRA[@]+"${PYTEST_EXTRA[@]}"}" \
         --timeout=600 --tb=short -q 2>&1; then
        PASSED=$((PASSED + 1))
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 5 ]]; then
            # pytest exit code 5 = no tests collected (all skipped)
            SKIPPED=$((SKIPPED + 1))
        else
            FAILED=$((FAILED + 1))
            FAIL_LIST+=("$BASENAME")
        fi
    fi

    cleanup_tmp
    echo ""
done

echo "========================================="
echo "Integration test summary"
echo "  Total files : ${TOTAL}"
echo "  Passed      : ${PASSED}"
echo "  Failed      : ${FAILED}"
echo "  Skipped     : ${SKIPPED}"
if [[ ${#FAIL_LIST[@]} -gt 0 ]]; then
    echo "  Failures    :"
    for f in "${FAIL_LIST[@]}"; do
        echo "    - $f"
    done
fi
echo "========================================="

[[ $FAILED -eq 0 ]]
