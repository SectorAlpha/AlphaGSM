#!/usr/bin/env bash

set -Eeuo pipefail
set -x

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$_SCRIPT_DIR/../.." && pwd))"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ALPHAGSM_SCRIPT="$REPO_ROOT/alphagsm"

START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"
SERVER_NAME="${SERVER_NAME:-itns2server}"
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
WORK_DIR="$(mktemp -d "$SMOKE_WORK_ROOT/ns2server-smoke-XXXXXX")"
HOME_DIR="$WORK_DIR/alphagsm-home"
INSTALL_DIR="$WORK_DIR/ns2server-server"
CONFIG_PATH="$WORK_DIR/alphagsm-ns2server.conf"
EXPECTED_PROTOCOL="a2s"

mkdir -p "$HOME_DIR"

PORT="$(pick_free_port_group 4)"

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
sessiontag = AlphaGSM-ns2-IT#
keeplogs = 1
EOF

echo "Using install dir: $INSTALL_DIR"
echo "Using port: $PORT"

run_create_or_skip_disabled "$SERVER_NAME" create ns2server
run_alphagsm "$SERVER_NAME" set httpport "$((PORT + 2))"
run_alphagsm "$SERVER_NAME" set webdomain "127.0.0.1"
run_alphagsm "$SERVER_NAME" set modserverport "$((PORT + 3))"
run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"

WORKSHOP_IDS=""
if [[ -n "${NS2_WORKSHOP_COLLECTION:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop-collection "$NS2_WORKSHOP_COLLECTION"
elif [[ -n "${NS2_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod add workshop "$NS2_WORKSHOP_ITEM"
fi
if [[ -n "${NS2_WORKSHOP_COLLECTION:-}${NS2_WORKSHOP_ITEM:-}" ]]; then
  run_alphagsm "$SERVER_NAME" mod apply
  WORKSHOP_IDS="$("$PYTHON_BIN" - "$HOME_DIR/conf/$SERVER_NAME.json" <<'PYIDS'
import json, sys
with open(sys.argv[1]) as handle:
    print(" ".join(row["workshop_id"] for row in json.load(handle)["mods"]["desired"]["workshop"]))
PYIDS
)"
fi

run_alphagsm "$SERVER_NAME" start
SERVER_STARTED=1
wait_for_info_protocol "$SERVER_NAME" "$EXPECTED_PROTOCOL" "$START_TIMEOUT_SECONDS"
if [[ -n "${WORKSHOP_IDS:-}" ]]; then
  ALPHAGSM_CONFIG_LOCATION="$CONFIG_PATH" PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT" \
    "$PYTHON_BIN" - "$ALPHAGSM_SCRIPT" "$SERVER_NAME" "$((PORT + 2))" "${NS2_WORKSHOP_MAP:-ns2_jambi}" "${NS2_WORKSHOP_LOAD_ITEM:-${WORKSHOP_IDS%% *}}" <<'PYLOAD'
import json, subprocess, sys, time
from tests.smoke_tests.ns2_workshop import read_map_origins, assert_map_origin, change_map
script, server, port, map_name, item = sys.argv[1:]
deadline, selected, error = time.monotonic() + 300, False, None
while time.monotonic() < deadline:
    try:
        assert_map_origin(read_map_origins('127.0.0.1', int(port), 'admin', 'CHANGE_ME'), map_name, item)
        if not selected:
            change_map('127.0.0.1', int(port), 'admin', 'CHANGE_ME', map_name)
            selected = True
        result = subprocess.run([sys.executable, script, server, 'info', '--json'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('protocol') == 'a2s' and data.get('map', '').lower() == map_name.lower():
                print(f'Engine executes {map_name} from native Workshop item {item}')
                break
    except (OSError, ValueError, AssertionError) as exc:
        error = exc
    time.sleep(2)
else:
    raise AssertionError(f'NS2 native Workshop map did not execute: {error}')
PYLOAD
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
