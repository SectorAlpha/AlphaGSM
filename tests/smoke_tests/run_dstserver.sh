#!/usr/bin/env bash
set -Eeuo pipefail

# A Klei provider token is required even though SteamCMD installs anonymously.
if [[ -z "${ALPHAGSM_DST_CLUSTER_SOURCE:-}" ]]; then
  echo 'DST requires ALPHAGSM_DST_CLUSTER_SOURCE containing cluster.ini, cluster_token.txt and Master/server.ini' >&2
  exit 77
fi
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itdstserver}"
SERVER_STARTED=0
WORKSHOP_ITEM_ID=378160973

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Required command not found: $1" >&2; exit 1; }
}
run_alphagsm() {
  echo "=== alphagsm $* ==="
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" \
    "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" "$@"
}
# shellcheck source=smoke_tests/steamcmd_helpers.sh
source "$REPO_ROOT/tests/smoke_tests/steamcmd_helpers.sh"
cleanup() {
  set +e
  if [[ "$SERVER_STARTED" == 1 ]]; then
    run_alphagsm "$SERVER_NAME" stop
  fi
}
trap cleanup EXIT
require_cmd "$PYTHON_BIN"
require_cmd screen
WORK_DIR="$(mktemp -d "$(resolve_work_root)/dstserver-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/dstserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-dstserver.conf"
CLUSTER_DIR="$INSTALL_DIR/DoNotStarveTogether/$SERVER_NAME"
LOG_PATH="$CLUSTER_DIR/Master/server_log.txt"
mkdir -p "$HOME_DIR"
PORT="$(pick_free_port_group 3)"
QUERY_PORT=$((PORT + 1))
AUTH_PORT=$((PORT + 2))
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
sessiontag = AlphaGSM-dstserver-IT#
keeplogs = 1
EOF
run_create_or_skip_disabled "$SERVER_NAME" create dstserver
run_alphagsm "$SERVER_NAME" set queryport "$QUERY_PORT"
run_alphagsm "$SERVER_NAME" set authport "$AUTH_PORT"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
"$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/dst_workshop.py" stage \
  "$ALPHAGSM_DST_CLUSTER_SOURCE" "$CLUSTER_DIR" "$PORT" "$QUERY_PORT" "$AUTH_PORT"
[[ ! -e "$LOG_PATH" ]]
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == 1 ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "https://steamcommunity.com/sharedfiles/filedetails/?id=$WORKSHOP_ITEM_ID"
  run_alphagsm "$SERVER_NAME" mod apply
fi
run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == 1 ]]; then
  "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/dst_workshop.py" verify "$LOG_PATH" --timeout "$START_TIMEOUT_SECONDS"
fi
wait_for_ready "$LOG_PATH" "$START_TIMEOUT_SECONDS" 'Online Server Started on port'
wait_for_info_protocol "$SERVER_NAME" a2s "$START_TIMEOUT_SECONDS" "$QUERY_PORT"
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" \
  "$SERVER_NAME" info --json > "$WORK_DIR/info.json"
"$PYTHON_BIN" - "$WORK_DIR/info.json" "$QUERY_PORT" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    info = json.load(handle)
assert info["protocol"] == "a2s", info
assert info["port"] == int(sys.argv[2]), info
assert info["players"] == 0, info
assert info["max_players"] > 0, info
PY
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0
run_alphagsm "$SERVER_NAME" status
"$PYTHON_BIN" - "$QUERY_PORT" "$STOP_TIMEOUT_SECONDS" <<'PY'
import socket
import sys
import time
deadline = time.monotonic() + int(sys.argv[2])
while time.monotonic() < deadline:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(2)
        try:
            sock.sendto(b"\xff\xff\xff\xffTSource Engine Query\x00", ("127.0.0.1", int(sys.argv[1])))
            sock.recv(4096)
        except OSError:
            break
    time.sleep(2)
else:
    raise AssertionError("DST still answers A2S after AlphaGSM stop")
PY
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == 1 ]]; then
  run_alphagsm "$SERVER_NAME" mod cleanup
  [[ ! -e "$CLUSTER_DIR/Master/modoverrides.lua" ]]
fi
