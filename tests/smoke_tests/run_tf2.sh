#!/usr/bin/env bash
set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STATUS_HELPER="$REPO_ROOT/tests/smoke_tests/source_status.py"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
STOP_TIMEOUT_SECONDS="${STOP_TIMEOUT_SECONDS:-90}"
SERVER_NAME="${SERVER_NAME:-ittf2}"
SERVER_STARTED=0
TF2_CURATED_REGISTRY_PATH="${TF2_CURATED_REGISTRY_PATH:-}"

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

# shellcheck source=tests/smoke_tests/steamcmd_helpers.sh
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
WORK_DIR="$(mktemp -d "$SMOKE_WORK_ROOT/tf2-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/tf2-server"
CONFIG_PATH="$WORK_DIR/alphagsm-tf2.conf"
LOG_PATH="$HOME_DIR/logs/AlphaGSM-TF2-IT#$SERVER_NAME.log"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port_group 6)"

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
sessiontag = AlphaGSM-TF2-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using UDP port: $PORT"

run_alphagsm "$SERVER_NAME" create teamfortress2
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

if [[ ! -f "$INSTALL_DIR/srcds_run_64" ]] && [[ ! -f "$INSTALL_DIR/srcds_run" ]]; then
  echo "Expected TF2 launcher not found in $INSTALL_DIR" >&2
  exit 1
fi
test -f "$INSTALL_DIR/tf/cfg/server.cfg"
# Keep the smoke server awake for real A2S query and info checks.
printf '\nsv_hibernate_when_empty 0\ntf_allow_server_hibernation 0\n' >> "$INSTALL_DIR/tf/cfg/server.cfg"

if [[ -n "$TF2_CURATED_REGISTRY_PATH" ]]; then
  echo "Applying curated TF2 mods from override registry: $TF2_CURATED_REGISTRY_PATH"
  ALPHAGSM_TF2_CURATED_REGISTRY_PATH="$TF2_CURATED_REGISTRY_PATH" run_alphagsm "$SERVER_NAME" mod add curated sourcemod
  ALPHAGSM_TF2_CURATED_REGISTRY_PATH="$TF2_CURATED_REGISTRY_PATH" run_alphagsm "$SERVER_NAME" mod apply
  test -f "$INSTALL_DIR/tf/addons/sourcemod/plugins/base.smx"
fi

WORKSHOP_IDS=""
if [[ -n "${TF2_WORKSHOP_COLLECTION:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop-collection "$TF2_WORKSHOP_COLLECTION"
elif [[ -n "${TF2_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "$TF2_WORKSHOP_ITEM"
fi
if [[ -n "${TF2_WORKSHOP_COLLECTION:-}${TF2_WORKSHOP_ITEM:-}" ]]; then
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
  WORKSHOP_MAP="${TF2_WORKSHOP_MAP:-cp_orange_x3}"
  WORKSHOP_ITEM="${TF2_WORKSHOP_LOAD_ITEM:-${WORKSHOP_IDS%% *}}"
  [[ "$WORKSHOP_ITEM" =~ ^[0-9]+$ ]] || exit 1
  [[ "$WORKSHOP_MAP" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 1
  # Download asynchronously while the engine can still answer native probes.
  run_alphagsm "$SERVER_NAME" send "tf_workshop_map_sync $WORKSHOP_ITEM"
  WORKSHOP_CHANGE_REQUESTED=0
  WORKSHOP_MAP_LOADED=0
  WORKSHOP_DEADLINE=$((SECONDS + 600))
  while (( SECONDS < WORKSHOP_DEADLINE )); do
    if [[ "$WORKSHOP_CHANGE_REQUESTED" == "0" ]]; then
      PROBE_TOKEN="AlphaGSM-TF2-$("$PYTHON_BIN" -c 'import uuid; print(uuid.uuid4().hex)')"
      run_alphagsm "$SERVER_NAME" send "echo BEGIN-$PROBE_TOKEN; tf_workshop_map_status; status; echo END-$PROBE_TOKEN"
      sleep 1
      run_alphagsm "$SERVER_NAME" logs -n 20000 > "$WORK_DIR/workshop-path.log"
      if "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/tf2_workshop.py" "$WORK_DIR/workshop-path.log" "$WORKSHOP_ITEM" "$WORKSHOP_MAP" "$PROBE_TOKEN" --ready-only; then
        run_alphagsm "$SERVER_NAME" send "changelevel workshop/$WORKSHOP_ITEM"
        WORKSHOP_CHANGE_REQUESTED=1
      fi
      sleep 2
      continue
    fi
    if run_alphagsm "$SERVER_NAME" info --json > "$WORK_DIR/workshop-info.json"; then
      if "$PYTHON_BIN" - "$WORK_DIR/workshop-info.json" "$WORKSHOP_MAP" "$WORKSHOP_ITEM" "$PORT" <<'PYMAP'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
canonical = f"workshop/{sys.argv[2]}.ugc{sys.argv[3]}"
assert data["protocol"] == "a2s" and data["port"] == int(sys.argv[4]), data
assert data["map"] in (sys.argv[2], canonical, canonical.removeprefix("workshop/")), data
PYMAP
      then
        PROBE_TOKEN="AlphaGSM-TF2-$("$PYTHON_BIN" -c 'import uuid; print(uuid.uuid4().hex)')"
        run_alphagsm "$SERVER_NAME" send "echo BEGIN-$PROBE_TOKEN; tf_workshop_map_status; status; echo END-$PROBE_TOKEN"
        sleep 1
        run_alphagsm "$SERVER_NAME" logs -n 20000 > "$WORK_DIR/workshop-path.log"
        if "$PYTHON_BIN" "$REPO_ROOT/tests/smoke_tests/tf2_workshop.py" "$WORK_DIR/workshop-path.log" "$WORKSHOP_ITEM" "$WORKSHOP_MAP" "$PROBE_TOKEN"; then
          WORKSHOP_MAP_LOADED=1
          break
        fi
      fi
    fi
    sleep 2
  done
  if [[ "$WORKSHOP_MAP_LOADED" != "1" ]]; then
    run_alphagsm "$SERVER_NAME" doctor --json || true
    run_alphagsm "$SERVER_NAME" logs -n 20000
    exit 1
  fi
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
