#!/usr/bin/env bash
set -Eeuo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$_SCRIPT_DIR" rev-parse --show-toplevel)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"
SERVER_NAME="${SERVER_NAME:-ittmlsmoke}"
SERVER_STARTED=0
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-900}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
RUNTIME_BACKEND="${ALPHAGSM_TEST_RUNTIME_BACKEND:-process}"
mkdir -p "${ALPHAGSM_WORK_DIR:-/tmp}"
WORK_DIR="$(mktemp -d "${ALPHAGSM_WORK_DIR:-/tmp}/tmodloader-smoke.XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/server"
CONFIG_PATH="$WORK_DIR/alphagsm.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-TML-Smoke#$SERVER_NAME.log"
mkdir -p "$HOME_DIR"
export ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH"
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src"

run_alphagsm() {
  "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}

# shellcheck source=tests/smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"

cleanup() {
  if [[ "$SERVER_STARTED" == "1" ]]; then
    run_alphagsm "$SERVER_NAME" stop || true
  fi
}
trap cleanup EXIT
PORT="$(pick_free_port)"
cat > "$CONFIG_PATH" <<EOF
[core]
alphagsm_path = $HOME_DIR
userconf = $HOME_DIR
[downloader]
db_path = $HOME_DIR/downloads/downloads.txt
target_path = $HOME_DIR/downloads/downloads
[downloader.steamcmd]
steamcmd_path = $WORK_DIR/steamcmd
[server]
datapath = $HOME_DIR/conf
[screen]
screenlog_path = $HOME_DIR/logs
sessiontag = AlphaGSM-TML-Smoke#
keeplogs = 1
[runtime]
backend = $RUNTIME_BACKEND
EOF

run_alphagsm "$SERVER_NAME" create terraria.tmodloader
if [[ "$RUNTIME_BACKEND" == "docker" && -n "${ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX:-}" ]]; then
  run_alphagsm "$SERVER_NAME" set image "$ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX"
fi
run_alphagsm "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == "1" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop 2687866031
  run_alphagsm "$SERVER_NAME" mod apply
fi
SERVER_STARTED=1
run_alphagsm "$SERVER_NAME" start --autocreate
wait_for_info_protocol "$SERVER_NAME" terraria "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == "1" ]]; then
  "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/tmodloader_workshop.py" "$SERVER_NAME"
fi
run_alphagsm "$SERVER_NAME" stop
SERVER_STARTED=0
run_alphagsm "$SERVER_NAME" status
"$PYTHON_BIN" - "$PORT" "$STOP_TIMEOUT_SECONDS" <<'PY'
import socket
import sys
import time
deadline = time.monotonic() + int(sys.argv[2])
while time.monotonic() < deadline:
    try:
        with socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=1):
            pass
    except OSError:
        break
    time.sleep(1)
else:
    raise SystemExit('tModLoader still accepts connections after stop')
PY
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == "1" ]]; then
  run_alphagsm "$SERVER_NAME" mod cleanup
fi
