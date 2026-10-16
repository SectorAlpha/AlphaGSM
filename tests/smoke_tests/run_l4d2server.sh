#!/usr/bin/env bash

set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"
STATUS_HELPER="$REPO_ROOT/tests/smoke_tests/source_status.py"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-300}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-itl4d2server}"
SERVER_STARTED=0
L4D2_WORKSHOP_COLLECTION="${ALPHAGSM_L4D2_WORKSHOP_COLLECTION:-}"
L4D2_WORKSHOP_ITEM="${ALPHAGSM_L4D2_WORKSHOP_ITEM:-}"
if [[ "${ALPHAGSM_RUN_L4D2_WORKSHOP:-0}" == "1" ]]; then
  L4D2_WORKSHOP_COLLECTION="${L4D2_WORKSHOP_COLLECTION:-https://steamcommunity.com/sharedfiles/filedetails/?id=121115793}"
  L4D2_WORKSHOP_ITEM="${L4D2_WORKSHOP_ITEM:-https://steamcommunity.com/sharedfiles/filedetails/?id=214630948}"
fi
WORKSHOP_IDS=()

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

WORK_DIR="$(mktemp -d)"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/l4d2server-server"
CONFIG_PATH="$WORK_DIR/alphagsm-l4d2server.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-l4d2server-IT#$SERVER_NAME.log"

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
sessiontag = AlphaGSM-l4d2server-IT#
keeplogs = 1

# Keep the smoke server awake for real A2S query and info checks.
[gamemodules.l4d2server.servercfg]
sv_hibernate_when_empty = 0
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create l4d2server
run_alphagsm "$SERVER_NAME" workshop list
if [[ -n "$L4D2_WORKSHOP_ITEM" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "$L4D2_WORKSHOP_ITEM"
fi
if [[ -n "$L4D2_WORKSHOP_COLLECTION" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop-collection "$L4D2_WORKSHOP_COLLECTION"
fi
if [[ -n "$L4D2_WORKSHOP_COLLECTION" || -n "$L4D2_WORKSHOP_ITEM" ]]; then
  mapfile -t WORKSHOP_IDS < <("$PYTHON_BIN" - "$HOME_DIR/conf/$SERVER_NAME.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
for entry in data["mods"]["desired"]["workshop"]:
    print(entry["workshop_id"])
PY
  )
  [[ "${#WORKSHOP_IDS[@]}" -gt 0 ]]
fi
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"
if [[ -n "${L4D2_WORKSHOP_COLLECTION:-}${L4D2_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod apply
fi

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"
if [[ -n "${L4D2_WORKSHOP_COLLECTION:-}${L4D2_WORKSHOP_ITEM:-}" ]]; then
  probe_nonce="$("$PYTHON_BIN" -c 'import uuid; print(uuid.uuid4().hex)')"
  probe_begin="AlphaGSM-Workshop-Mounts-BEGIN-$probe_nonce"
  probe_end="AlphaGSM-Workshop-Mounts-END-$probe_nonce"
  run_alphagsm "$SERVER_NAME" send "echo $probe_begin"
  run_alphagsm "$SERVER_NAME" send "show_addon_load_order"
  run_alphagsm "$SERVER_NAME" send "echo $probe_end"
  mount_deadline=$((SECONDS + 60))
  until "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/l4d2_workshop.py" "$LOG_PATH" "${WORKSHOP_IDS[@]}" --begin-marker "$probe_begin" --end-marker "$probe_end"; do
    [[ "$SECONDS" -lt "$mount_deadline" ]] || exit 1
    sleep 1
  done
fi
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
