#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itunturned}"
SERVER_STARTED=0
WORKSHOP_MAP_ID="2396897717"
WORKSHOP_MAP_NAME="PEI Arena"

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
}

trap cleanup EXIT

require_cmd "$PYTHON_BIN"
require_cmd screen

WORK_DIR="$(mktemp -d "$(resolve_work_root)/unturned-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/unturned-server"
CONFIG_PATH="$WORK_DIR/alphagsm-unturned.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-unturned-IT#$SERVER_NAME.log"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port_group 2)"

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
sessiontag = AlphaGSM-unturned-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create unturned
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == "1" ]]; then
  [[ ! -e "$INSTALL_DIR/Maps/$WORKSHOP_MAP_NAME" ]]
  run_alphagsm "$SERVER_NAME" mod add workshop "$WORKSHOP_MAP_ID"
  run_alphagsm "$SERVER_NAME" mod apply
  printf 'Map %s\n' "$WORKSHOP_MAP_NAME" >> "$INSTALL_DIR/Servers/$SERVER_NAME/Server/Commands.dat"
fi

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_ready "$LOG_PATH" "$START_TIMEOUT_SECONDS" 'Loading level: 100%'
run_alphagsm "$SERVER_NAME" status
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
# Read JSON directly so this assertion proves the live engine's map/protocol.
ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src" "$PYTHON_BIN" "$ALPHAGSM_SCRIPT" \
  "$SERVER_NAME" info --json > "$WORK_DIR/info.json"
"$PYTHON_BIN" - "$WORK_DIR/info.json" "${ALPHAGSM_RUN_WORKSHOP:-0}" "$WORKSHOP_MAP_NAME" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    info = json.load(handle)
assert info["protocol"] == "a2s", info
assert info["players"] == 0, info
if sys.argv[2] == "1":
    assert info["map"] == sys.argv[3], f"Engine did not load the Workshop-only map: {info!r}"
PY
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
"$PYTHON_BIN" - "$PORT" "$STOP_TIMEOUT_SECONDS" <<'PY'
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
    raise AssertionError("Unturned still answers A2S after AlphaGSM stop")
PY
if [[ "${ALPHAGSM_RUN_WORKSHOP:-0}" == "1" ]]; then
  run_alphagsm "$SERVER_NAME" mod remove workshop "$WORKSHOP_MAP_ID"
  run_alphagsm "$SERVER_NAME" mod apply
  "$PYTHON_BIN" - "$INSTALL_DIR/Servers/$SERVER_NAME/WorkshopDownloadConfig.json" "$WORKSHOP_MAP_ID" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    assert int(sys.argv[2]) not in json.load(handle)["File_IDs"]
PY
fi
