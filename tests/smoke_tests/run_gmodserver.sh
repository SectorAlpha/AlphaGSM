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
SERVER_NAME="${SERVER_NAME:-itgmodserver}"
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

SMOKE_WORK_ROOT="${ALPHAGSM_WORK_DIR:-${TMPDIR:-/tmp}}"
mkdir -p "$SMOKE_WORK_ROOT"
WORK_DIR="$(mktemp -d "$SMOKE_WORK_ROOT/gmod-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/gmodserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-gmodserver.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-gmodserver-IT#$SERVER_NAME.log"

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
sessiontag = AlphaGSM-gmodserver-IT#
keeplogs = 1

# Keep the smoke server awake for real A2S query and info checks.
[gamemodules.gmodserver.servercfg]
sv_hibernate_when_empty = 0
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create gmodserver
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

# Optional public Workshop fixture/collection. Each selected addon must mount in-engine.
WORKSHOP_IDS=""
if [[ -n "${GMOD_WORKSHOP_COLLECTION:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop-collection "$GMOD_WORKSHOP_COLLECTION"
elif [[ -n "${GMOD_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "$GMOD_WORKSHOP_ITEM"
fi
if [[ -n "${GMOD_WORKSHOP_COLLECTION:-}${GMOD_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod apply
  WORKSHOP_IDS="$("$PYTHON_BIN" - "$HOME_DIR/conf/$SERVER_NAME.json" <<'PYIDS'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(" ".join(entry["workshop_id"] for entry in data["mods"]["desired"]["workshop"]))
PYIDS
)"
fi

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"
run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" status
if [[ -n "${WORKSHOP_IDS:-}" ]]; then
  PROBE_TOKEN="AlphaGSM-Workshop-$("$PYTHON_BIN" -c 'import uuid; print(uuid.uuid4().hex)')"
  PROBE_COMMAND="$("$PYTHON_BIN" - "$HOME_DIR/conf/$SERVER_NAME.json" "$PROBE_TOKEN" "$_SCRIPT_DIR" <<'PYPROBE'
import json
import sys
sys.path.insert(0, sys.argv[3])
from gmod_workshop import write_probe
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(write_probe(data, sys.argv[2]))
PYPROBE
)"
  run_alphagsm "$SERVER_NAME" send "$PROBE_COMMAND"
  PROBE_LOG="$WORK_DIR/workshop-probe.log"
  PROBE_COMPLETE=0
  for (( attempt=0; attempt<60; attempt++ )); do
    run_alphagsm "$SERVER_NAME" logs -n 20000 > "$PROBE_LOG"
    read -r -a WORKSHOP_ID_ARGS <<< "$WORKSHOP_IDS"
    if "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/gmod_workshop.py" "$PROBE_LOG" "$PROBE_TOKEN" "${WORKSHOP_ID_ARGS[@]}"; then
      PROBE_COMPLETE=1
      break
    fi
    sleep 1
  done
  [[ "$PROBE_COMPLETE" == "1" ]] || { cat "$PROBE_LOG"; exit 1; }
fi
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status
