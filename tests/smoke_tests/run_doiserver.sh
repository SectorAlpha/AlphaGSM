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
SERVER_NAME="${SERVER_NAME:-itdoiserver}"
SERVER_STARTED=0

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

run_alphagsm() {
  echo >&2
  echo "=== alphagsm $* ===" >&2
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
WORK_DIR="$(mktemp -d "$SMOKE_WORK_ROOT/doiserver-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/doiserver-server"
CONFIG_PATH="$WORK_DIR/alphagsm-doiserver.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-doiserver-IT#$SERVER_NAME.log"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port_group 3)"

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
sessiontag = AlphaGSM-doiserver-IT#
keeplogs = 1

# Keep the smoke server awake for real A2S query and info checks.
[gamemodules.doiserver.servercfg]
sv_hibernate_when_empty = 0
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create doiserver
run_alphagsm "$SERVER_NAME" set clientport "$((PORT + 1))"
run_alphagsm "$SERVER_NAME" set sourcetvport "$((PORT + 2))"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"


WORKSHOP_IDS=""
if [[ -n "${DOI_WORKSHOP_COLLECTION:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop-collection "$DOI_WORKSHOP_COLLECTION"
elif [[ -n "${DOI_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "$DOI_WORKSHOP_ITEM"
fi
if [[ -n "${DOI_WORKSHOP_COLLECTION:-}${DOI_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod apply
  WORKSHOP_IDS="$("$PYTHON_BIN" - "$HOME_DIR/conf/$SERVER_NAME.json" <<'PYIDS'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(" ".join(entry["workshop_id"] for entry in data["mods"]["desired"]["workshop"]))
PYIDS
)"
fi

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "a2s" "$START_TIMEOUT_SECONDS"

if [[ -n "${WORKSHOP_IDS:-}" ]]; then
  read -r -a WORKSHOP_ID_ARGS <<< "$WORKSHOP_IDS"
  WORKSHOP_MOUNTED=0
  for (( attempt=0; attempt<120; attempt++ )); do
    PROBE_TOKEN="AlphaGSM-DOI-$("$PYTHON_BIN" -c 'import uuid; print(uuid.uuid4().hex)')"
    run_alphagsm "$SERVER_NAME" send "echo BEGIN-$PROBE_TOKEN; path; echo END-$PROBE_TOKEN"
    sleep 2
    run_alphagsm "$SERVER_NAME" logs -n 20000 > "$WORK_DIR/workshop-probe.log"
    if "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/nwi_workshop.py" "$WORK_DIR/workshop-probe.log" 447820 "$PROBE_TOKEN" "${WORKSHOP_ID_ARGS[@]}"; then
      WORKSHOP_MOUNTED=1
      break
    fi
  done
  [[ "$WORKSHOP_MOUNTED" == "1" ]] || { cat "$WORK_DIR/workshop-probe.log"; exit 1; }
  WORKSHOP_MAP="${DOI_WORKSHOP_MAP:-stalingrad}"
  WORKSHOP_MODE="${DOI_WORKSHOP_MODE:-offensive}"
  [[ "$WORKSHOP_MAP" =~ ^[a-zA-Z0-9_/-]+$ && "$WORKSHOP_MODE" =~ ^[a-zA-Z0-9_]+$ ]] || exit 1
  run_alphagsm "$SERVER_NAME" send "changelevel $WORKSHOP_MAP $WORKSHOP_MODE"
  WORKSHOP_MAP_LOADED=0
  for (( attempt=0; attempt<90; attempt++ )); do
    if run_alphagsm "$SERVER_NAME" info --json > "$WORK_DIR/workshop-info.json"; then
      if "$PYTHON_BIN" - "$WORK_DIR/workshop-info.json" "$WORKSHOP_MAP" <<'PYMAP'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
assert data["protocol"] == "a2s" and data["map"] == sys.argv[2], data
PYMAP
      then
        WORKSHOP_MAP_LOADED=1
        break
      fi
    fi
    sleep 2
  done
  [[ "$WORKSHOP_MAP_LOADED" == "1" ]] || { run_alphagsm "$SERVER_NAME" logs -n 20000; exit 1; }
fi

run_alphagsm "$SERVER_NAME" query
run_alphagsm "$SERVER_NAME" info
run_alphagsm "$SERVER_NAME" info --json
run_alphagsm "$SERVER_NAME" status
run_stop_or_skip "$SERVER_NAME"
SERVER_STARTED=0

run_alphagsm "$SERVER_NAME" status

if [[ -n "${WORKSHOP_IDS:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod cleanup
fi
