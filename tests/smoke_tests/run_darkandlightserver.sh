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
DEFAULT_WORK_ROOT="/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme"
LOCAL_DOCKER_IMAGE="alphagsm-wine-proton-runtime:local"
PUBLISHED_DOCKER_IMAGE="ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"

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

wait_for_generic_udp_closed() {
  local host="$1"
  local port="$2"
  local timeout_seconds="$3"

  EXPECTED_HOST="$host" EXPECTED_PORT="$port" TIMEOUT_SECONDS="$timeout_seconds" "$PYTHON_BIN" - <<'PY'
import os
import socket
import sys
import time

host = os.environ["EXPECTED_HOST"]
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

resolve_docker_image() {
  if [[ -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON:-}" ]]; then
    printf '%s\n' "$ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON"
    return 0
  fi

  if docker image inspect "$LOCAL_DOCKER_IMAGE" >/dev/null 2>&1; then
    printf '%s\n' "$LOCAL_DOCKER_IMAGE"
    return 0
  fi

  printf '%s\n' "$PUBLISHED_DOCKER_IMAGE"
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
require_cmd docker

DOCKER_IMAGE="$(resolve_docker_image)"
WORK_ROOT="${ALPHAGSM_WORK_DIR:-$DEFAULT_WORK_ROOT}"
mkdir -p "$WORK_ROOT"
WORK_DIR="$(mktemp -d -p "$WORK_ROOT" darkandlightserver-smoke.XXXXXX)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/darkandlightserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-darkandlightserver.conf"

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

[runtime]
backend = docker

[process]
backend = subprocess

[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-darkandlig-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create darkandlightserver
run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "udp" "$START_TIMEOUT_SECONDS"
query_output="$(run_alphagsm_capture "$SERVER_NAME" query)"
grep -F "Server port is open (UDP ping on port $PORT" <<<"$query_output" >/dev/null
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
wait_for_generic_udp_closed "127.0.0.1" "$PORT" "$STOP_TIMEOUT_SECONDS"

run_alphagsm "$SERVER_NAME" status
