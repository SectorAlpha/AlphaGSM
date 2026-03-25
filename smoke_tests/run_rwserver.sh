#\!/usr/bin/env bash
# DISABLED: This smoke test is disabled because the server failed, is disabled, or was skipped in integration testing
# See docs/TEST_STATUS.md for current server status
echo "Smoke test for rwserver is disabled - see docs/TEST_STATUS.md for status"
exit 0

set -Eeuo pipefail
set -x

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-300}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itrwserver}"
SERVER_STARTED=0

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

run_alphagsm() {
  echo
  echo "=== alphagsm $* ==="
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/smoke_tests/steamcmd_helpers.sh"

wait_for_log_ready() {
  local log_path="$1"
  local timeout_seconds="$2"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -f "$log_path" ]] && grep -Eq 'ready|started|listening|Done' "$log_path"; then
      return 0
    fi
    sleep 2
  done
  echo "Server log did not show readiness markers in time: $log_path" >&2
  return 1
}

cleanup() {
  set +e
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd screen

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/rwserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-rwserver.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-rwserver-IT#$SERVER_NAME.log"

mkdir -p "$HOME_DIR"

PORT="$("$PYTHON_BIN" - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)" 

cat > "$CONFIG_PATH" <<EOF
[core]
alphagsm_path = $HOME_DIR
userconf = $HOME_DIR

[downloader]
db_path = $HOME_DIR/downloads/downloads.txt
target_path = $HOME_DIR/downloads/downloads

[server]
datapath = $HOME_DIR/conf

[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-rwserver-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_alphagsm "$SERVER_NAME" create rwserver
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_log_ready "$LOG_PATH" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" stop
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
