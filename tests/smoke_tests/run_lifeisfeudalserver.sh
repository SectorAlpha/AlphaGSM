#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
SERVER_NAME="${SERVER_NAME:-smokelifdb}"
SERVER_STARTED=0
DB_CONTAINER_NAME="alphagsm-lif-db-$SERVER_NAME"

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
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"

cleanup() {
  set +e
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
  docker rm -f "$DB_CONTAINER_NAME" >/dev/null 2>&1 || true
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd screen
require_cmd docker

WORK_DIR="${TMPDIR:-/tmp}"
WORK_DIR="$(mktemp -d "$WORK_DIR/lif-smoke.XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/lifeisfeudalserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-lifeisfeudalserver.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-lifeisfeud-IT#$SERVER_NAME.log"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port)"
DB_PORT="$(pick_free_port)"

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
sessiontag = AlphaGSM-lifeisfeud-IT#
keeplogs = 1
EOF

docker rm -f "$DB_CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Using install dir: $INSTALL_DIR"
echo "Using game port: $PORT"
echo "Using managed DB port: $DB_PORT"

run_create_or_skip_disabled "$SERVER_NAME" create lifeisfeudalserver
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
run_alphagsm "$SERVER_NAME" set db_mode docker
run_alphagsm "$SERVER_NAME" set db_host 127.0.0.1
run_alphagsm "$SERVER_NAME" set db_port "$DB_PORT"
run_alphagsm "$SERVER_NAME" set db_name lif_1
run_alphagsm "$SERVER_NAME" set db_user root
run_alphagsm "$SERVER_NAME" set db_password alphagsm-lif-secret

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_ready "$LOG_PATH" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
