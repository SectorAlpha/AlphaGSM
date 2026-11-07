#!/usr/bin/env bash

set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itheatserver}"
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

# shellcheck source=tests/smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"


cleanup() {
  set +e
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

wait_for_heat_ready() {
  local log_dir="$1"
  local timeout_seconds="$2"
  local deadline=$((SECONDS + timeout_seconds))
  local patterns='Game has started\.|Type /shutdown to shut down the server\.'
  while (( SECONDS < deadline )); do
    local matched=0
    shopt -s nullglob
    local logs=( "$log_dir"/Console*.txt "$log_dir"/Dedi*.txt )
    shopt -u nullglob
    for log_path in "${logs[@]}"; do
      if [[ -f "$log_path" ]] && grep -Eiq "$patterns" "$log_path"; then
        return 0
      fi
      matched=1
    done
    sleep 2
  done
  echo "[diagnostic] Heat logs did not show readiness markers in ${timeout_seconds}s" >&2
  if [[ -d "$log_dir" ]]; then
    shopt -s nullglob
    local logs=( "$log_dir"/Console*.txt "$log_dir"/Dedi*.txt )
    shopt -u nullglob
    if (( ${#logs[@]} > 0 )); then
      for log_path in "${logs[@]}"; do
        echo "[diagnostic] Log tail: ${log_path}" >&2
        tail -100 "$log_path" >&2
      done
    else
      echo "[diagnostic] No Heat log files found in ${log_dir}" >&2
    fi
  else
    echo "[diagnostic] Heat log directory not found: ${log_dir}" >&2
  fi
  return 1
}

require_cmd "$PYTHON_BIN"
require_cmd screen
require_proton

WORK_ROOT="$(resolve_work_root)"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" heatserver-smoke-XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/heatserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-heatserver.conf"
LOG_DIR="$INSTALL_DIR/Logs"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port)" 
QUERY_PORT="$(pick_free_port)"
while [[ "$QUERY_PORT" == "$PORT" ]]; do
  QUERY_PORT="$(pick_free_port)"
done

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
sessiontag = AlphaGSM-heatserver-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"
echo "Using query port: $QUERY_PORT"

run_create_or_skip_disabled "$SERVER_NAME" create heatserver
run_alphagsm "$SERVER_NAME" set queryport "$QUERY_PORT"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_heat_ready "$LOG_DIR" "$START_TIMEOUT_SECONDS"
wait_for_info_protocol "$SERVER_NAME" a2s "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
