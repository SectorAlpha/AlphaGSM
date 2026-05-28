#!/usr/bin/env bash

set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itdarkandlig}"
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

run_alphagsm_capture() {
  local output_file
  output_file="$(mktemp)"
  echo
  echo "=== alphagsm $* ==="
  set +e
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" \
    "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@" >"$output_file" 2>&1
  local status=$?
  set -e
  RUN_CAPTURED_OUTPUT="$(cat "$output_file")"
  printf '%s\n' "$RUN_CAPTURED_OUTPUT"
  rm -f "$output_file"
  return "$status"
}

tail_if_exists() {
  local path="$1"
  local line_count="${2:-40}"
  if [[ ! -f "$path" ]]; then
    echo "<missing: $path>"
    return 0
  fi
  if [[ ! -s "$path" ]]; then
    echo "<empty: $path>"
    return 0
  fi
  tail -n "$line_count" "$path"
}

wait_for_udp_or_fail_fast() {
  local server_name="$1"
  local timeout_seconds="$2"
  local deadline=$((SECONDS + timeout_seconds))
  local screen_log_path="$HOME_DIR/logs/AlphaGSM-darkandlig-IT#$server_name.log"

  while (( SECONDS < deadline )); do
    if run_alphagsm_capture "$server_name" info --json >/dev/null; then
      if EXPECTED_PORT="$PORT" INFO_JSON_PAYLOAD="$RUN_CAPTURED_OUTPUT" "${PYTHON_BIN:-python3}" - <<'PY'
import json
import os

expected_port = int(os.environ["EXPECTED_PORT"])
data = json.loads(os.environ["INFO_JSON_PAYLOAD"])
assert data["protocol"] == "udp", data
assert data["port"] == expected_port, data
PY
      then
        return 0
      fi
    fi

    local status_output
    status_output="$(run_alphagsm_capture "$server_name" status || true)"
    if grep -F "Server isn't running as no screen session" <<<"$status_output" >/dev/null; then
      echo "[diagnostic] Dark and Light screen session died before UDP readiness" >&2
      echo "[diagnostic] status output:" >&2
      printf '%s\n' "$status_output" >&2
      echo "[diagnostic] screen log tail ($screen_log_path):" >&2
      tail_if_exists "$screen_log_path" >&2
      echo "[diagnostic] DNL log tail ($LOG_PATH):" >&2
      tail_if_exists "$LOG_PATH" >&2
      exit 1
    fi

    sleep 5
  done

  echo "[diagnostic] Dark and Light never reached UDP readiness in ${timeout_seconds}s" >&2
  echo "[diagnostic] screen log tail ($screen_log_path):" >&2
  tail_if_exists "$screen_log_path" >&2
  echo "[diagnostic] DNL log tail ($LOG_PATH):" >&2
  tail_if_exists "$LOG_PATH" >&2
  exit 1
}

wait_for_generic_udp_closed() {
  local port="$1"
  local timeout_seconds="$2"

  EXPECTED_PORT="$port" TIMEOUT_SECONDS="$timeout_seconds" "${PYTHON_BIN:-python3}" - <<'PY'
import os
import socket
import sys
import time

host = "127.0.0.1"
port = int(os.environ["EXPECTED_PORT"])
deadline = time.time() + int(os.environ["TIMEOUT_SECONDS"])

while time.time() < deadline:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2)
            sock.connect((host, port))
            sock.send(b"\x00")
            try:
                sock.recv(1)
            except socket.timeout:
                pass
    except OSError:
        sys.exit(0)
    time.sleep(2)

raise SystemExit(
    f"UDP port {host}:{port} still accepts traffic after {os.environ['TIMEOUT_SECONDS']}s"
)
PY
}

# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"


cleanup() {
  set +e
  if [[ "${SERVER_STARTED:-0}" == "1" ]] && [[ -n "${CONFIG_PATH:-}" && -f "${CONFIG_PATH:-}" ]]; then
    ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$SERVER_NAME" stop
  fi
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd screen
require_proton

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/darkandlightserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-darkandlightserver.conf"
LOG_PATH="$INSTALL_DIR/DNL/Saved/Logs/DNL.log"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port)" 

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
sessiontag = AlphaGSM-darkandlig-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create darkandlightserver
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_udp_or_fail_fast "$SERVER_NAME" "$START_TIMEOUT_SECONDS"
query_output="$(run_alphagsm_capture "$SERVER_NAME" query)"
grep -F "Server port is open (UDP ping on port $PORT" <<<"$query_output" >/dev/null

run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
wait_for_generic_udp_closed "$PORT" "$STOP_TIMEOUT_SECONDS"

run_alphagsm "$SERVER_NAME" status
