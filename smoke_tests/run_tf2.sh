#!/usr/bin/env bash
set -Eeuo pipefail
set -x

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
STATUS_HELPER="$REPO_ROOT/smoke_tests/source_status.py"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-ittf2}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

run_alphagsm() {
  echo
  echo "=== alphagsm $* ==="
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

cleanup() {
  set +e
  if [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd screen

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/tf2-server"
CONFIG_PATH="$WORK_DIR/alphagsm-tf2.conf"

mkdir -p "$HOME_DIR"

PORT="$("$PYTHON_BIN" - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
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
sessiontag = AlphaGSM-TF2-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using UDP port: $PORT"

run_alphagsm "$SERVER_NAME" create teamfortress2
run_alphagsm "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

test -f "$INSTALL_DIR/srcds_run"
test -f "$INSTALL_DIR/tf/cfg/server.cfg"

run_alphagsm "$SERVER_NAME" start
"$PYTHON_BIN" "$STATUS_HELPER" wait-for-status 127.0.0.1 "$PORT" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" stop
"$PYTHON_BIN" "$STATUS_HELPER" wait-for-closed 127.0.0.1 "$PORT" "$STOP_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
